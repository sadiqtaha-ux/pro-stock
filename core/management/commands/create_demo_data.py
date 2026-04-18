"""
core/management/commands/create_demo_data.py
Génération de données de démonstration pour MediCare Industries StockPro.

Usage:
    python manage.py create_demo_data
    python manage.py create_demo_data --reset  (efface les données existantes avant)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class Command(BaseCommand):
    help = "Génère les utilisateurs et matières premières de démonstration pour MediCare Industries."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les données existantes avant de régénérer.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from core.models import Utilisateur
        from produits.models import Fournisseur, UnitesMesure, MatierePremiere

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== StockPro Demo Data Generator ===\n"))

        # -----------------------------------
        # 0. RESET optionnel
        # -----------------------------------
        if options["reset"]:
            MatierePremiere.objects.all().delete()
            Fournisseur.objects.all().delete()
            UnitesMesure.objects.all().delete()
            Utilisateur.objects.filter(username__in=[
                "admin", "gestionnaire", "acheteur"
            ]).delete()
            self.stdout.write(self.style.WARNING("  ✓ Données existantes supprimées."))

        # -----------------------------------
        # 1. UTILISATEURS
        # -----------------------------------
        self.stdout.write("  Création des utilisateurs...")

        users_data = [
            {
                "username":   "admin",
                "password":   "admin123",
                "first_name": "Administrateur",
                "last_name":  "StockPro",
                "email":      "admin@medicare.ma",
                "role":       Utilisateur.Role.ADMIN,
                "service":    "Direction Informatique",
                "telephone":  "+212 6 00 00 00 01",
                "is_staff":   True,
                "is_superuser": True,
            },
            {
                "username":   "gestionnaire",
                "password":   "gest123",
                "first_name": "Youssef",
                "last_name":  "Benali",
                "email":      "gestionnaire@medicare.ma",
                "role":       Utilisateur.Role.RESPONSABLE_STOCK,
                "service":    "Gestion des Stocks",
                "telephone":  "+212 6 00 00 00 02",
                "is_staff":   False,
                "is_superuser": False,
            },
            {
                "username":   "acheteur",
                "password":   "achat123",
                "first_name": "Fatima",
                "last_name":  "Zahra",
                "email":      "acheteur@medicare.ma",
                "role":       Utilisateur.Role.ACHETEUR,
                "service":    "Approvisionnement",
                "telephone":  "+212 6 00 00 00 03",
                "is_staff":   False,
                "is_superuser": False,
            },
        ]

        for u in users_data:
            password = u.pop("password")
            obj, created = Utilisateur.objects.get_or_create(
                username=u["username"],
                defaults={**u, "password": make_password(password), "est_actif": True},
            )
            if created:
                self.stdout.write(f"    ✓ {obj.username} ({obj.get_role_display()}) — créé  [mdp: {password}]")
            else:
                self.stdout.write(f"    ~ {obj.username} — déjà existant, ignoré.")

        # -----------------------------------
        # 2. UNITÉS DE MESURE
        # -----------------------------------
        self.stdout.write("  Création des unités de mesure...")

        unites_data = [
            ("Kilogramme", "kg"),
            ("Gramme",     "g"),
            ("Litre",      "L"),
            ("Millilitre", "mL"),
            ("Unité",      "u"),
            ("Boîte",      "boîte"),
            ("Sac",        "sac"),
        ]
        unites = {}
        for nom, symbole in unites_data:
            u, _ = UnitesMesure.objects.get_or_create(nom=nom, defaults={"symbole": symbole})
            unites[symbole] = u
            self.stdout.write(f"    ✓ {nom} ({symbole})")

        # -----------------------------------
        # 3. FOURNISSEURS
        # -----------------------------------
        self.stdout.write("  Création des fournisseurs...")

        fournisseurs_data = [
            {
                "nom":      "Sigma-Aldrich Maroc",
                "contact":  "Rachid El Amrani",
                "email":    "r.elamrani@sigma-aldrich.ma",
                "telephone":"+212 5 37 00 11 22",
                "ville":    "Casablanca",
                "pays":     "Maroc",
            },
            {
                "nom":      "BASF Pharma Maghreb",
                "contact":  "Nadia Tazi",
                "email":    "n.tazi@basf.ma",
                "telephone":"+212 5 22 00 33 44",
                "ville":    "Rabat",
                "pays":     "Maroc",
            },
            {
                "nom":      "Clariant Chemicals",
                "contact":  "Omar Benhaddou",
                "email":    "o.benhaddou@clariant.com",
                "telephone":"+212 5 22 77 88 99",
                "ville":    "Kénitra",
                "pays":     "Maroc",
            },
        ]

        fournisseurs = {}
        for f in fournisseurs_data:
            obj, created = Fournisseur.objects.get_or_create(
                nom=f["nom"], defaults={**f, "actif": True}
            )
            fournisseurs[f["nom"]] = obj
            action = "créé" if created else "déjà existant"
            self.stdout.write(f"    ✓ {obj.nom} — {action}")

        # -----------------------------------
        # 4. MATIÈRES PREMIÈRES — 10 APIs pharmaceutiques réalistes
        # -----------------------------------
        self.stdout.write("  Création des matières premières...")

        MP = MatierePremiere.Categorie
        METHODE = MatierePremiere.MethodeApprovisionnement
        ZONE = MatierePremiere.ZoneStockage
        F1 = fournisseurs["Sigma-Aldrich Maroc"]
        F2 = fournisseurs["BASF Pharma Maghreb"]
        F3 = fournisseurs["Clariant Chemicals"]

        matieres_data = [
            # Principes actifs
            {
                "reference": "API-001",
                "nom": "Paracétamol (Acétaminophène) USP",
                "description": "Principe actif analgésique et antipyrétique. Conforme Pharmacopée Européenne.",
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": unites["kg"],
                "fournisseur_principal": F1,
                "prix_unitaire": Decimal("320.00"),
                "stock_actuel": Decimal("250.000"),
                "stock_minimum": Decimal("80.000"),
                "stock_maximum": Decimal("600.000"),
                "stock_securite": Decimal("50.000"),
                "methode_approvisionnement": METHODE.POINT_COMMANDE,
                "point_commande": Decimal("100.000"),
                "qec": Decimal("200.000"),
                "delai_livraison_jours": 14,
                "zone_stockage": ZONE.SECHE,
                "emplacement": "A1",
            },
            {
                "reference": "API-002",
                "nom": "Amoxicilline Trihydrate",
                "description": "Antibiotique semi-synthétique de la famille des aminopénicillines. Grade pharmaceutique.",
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": unites["kg"],
                "fournisseur_principal": F2,
                "prix_unitaire": Decimal("1850.00"),
                "stock_actuel": Decimal("45.000"),
                "stock_minimum": Decimal("60.000"),
                "stock_maximum": Decimal("300.000"),
                "stock_securite": Decimal("30.000"),
                "methode_approvisionnement": METHODE.POINT_COMMANDE,
                "point_commande": Decimal("70.000"),
                "qec": Decimal("120.000"),
                "delai_livraison_jours": 21,
                "zone_stockage": ZONE.SECHE,
                "emplacement": "A2",
            },
            {
                "reference": "API-003",
                "nom": "Ibuprofène micronisé",
                "description": "AINS de la famille des propionates. Grade pharmaceutique pour formes orales solides.",
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": unites["kg"],
                "fournisseur_principal": F1,
                "prix_unitaire": Decimal("490.00"),
                "stock_actuel": Decimal("180.000"),
                "stock_minimum": Decimal("60.000"),
                "stock_maximum": Decimal("400.000"),
                "stock_securite": Decimal("40.000"),
                "methode_approvisionnement": METHODE.REAPPRO_FIXE,
                "point_commande": Decimal("80.000"),
                "qec": Decimal("150.000"),
                "delai_livraison_jours": 14,
                "periode_reappro_jours": 30,
                "zone_stockage": ZONE.SECHE,
                "emplacement": "A3",
            },
            {
                "reference": "API-004",
                "nom": "Metformine Chlorhydrate",
                "description": "Antidiabétique oral de la classe des biguanides. Conforme EP 10.",
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": unites["kg"],
                "fournisseur_principal": F2,
                "prix_unitaire": Decimal("275.00"),
                "stock_actuel": Decimal("0.000"),
                "stock_minimum": Decimal("50.000"),
                "stock_maximum": Decimal("350.000"),
                "stock_securite": Decimal("35.000"),
                "methode_approvisionnement": METHODE.POINT_COMMANDE,
                "point_commande": Decimal("60.000"),
                "qec": Decimal("180.000"),
                "delai_livraison_jours": 18,
                "zone_stockage": ZONE.SECHE,
                "emplacement": "A4",
            },
            {
                "reference": "API-005",
                "nom": "Atorvastatine Calcique",
                "description": "Statine hypolipidémiante de 3e génération. Pureté ≥ 99.5 %.",
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": unites["kg"],
                "fournisseur_principal": F1,
                "prix_unitaire": Decimal("8500.00"),
                "stock_actuel": Decimal("12.500"),
                "stock_minimum": Decimal("10.000"),
                "stock_maximum": Decimal("60.000"),
                "stock_securite": Decimal("8.000"),
                "methode_approvisionnement": METHODE.MRP,
                "qec": Decimal("25.000"),
                "delai_livraison_jours": 30,
                "taux_rebut": Decimal("0.0200"),
                "zone_stockage": ZONE.SECHE,
                "emplacement": "B1",
            },
            # Excipients
            {
                "reference": "EXC-001",
                "nom": "Cellulose Microcristalline (MCC) PH-102",
                "description": "Excipient de compression directe. Grade Pharmacopée Européenne.",
                "categorie": MP.EXCIPIENT,
                "unite": unites["kg"],
                "fournisseur_principal": F3,
                "prix_unitaire": Decimal("85.00"),
                "stock_actuel": Decimal("520.000"),
                "stock_minimum": Decimal("150.000"),
                "stock_maximum": Decimal("1000.000"),
                "stock_securite": Decimal("100.000"),
                "methode_approvisionnement": METHODE.RECOMPLETEMENT,
                "point_commande": Decimal("200.000"),
                "qec": Decimal("400.000"),
                "delai_livraison_jours": 7,
                "periode_reappro_jours": 30,
                "zone_stockage": ZONE.SECHE,
                "emplacement": "C1",
            },
            {
                "reference": "EXC-002",
                "nom": "Amidon de maïs prégélatinisé",
                "description": "Liant et désintégrant pharmaceutique. Conforme USNF.",
                "categorie": MP.EXCIPIENT,
                "unite": unites["kg"],
                "fournisseur_principal": F3,
                "prix_unitaire": Decimal("42.00"),
                "stock_actuel": Decimal("380.000"),
                "stock_minimum": Decimal("100.000"),
                "stock_maximum": Decimal("800.000"),
                "stock_securite": Decimal("80.000"),
                "methode_approvisionnement": METHODE.RECOMPLETEMENT,
                "qec": Decimal("300.000"),
                "delai_livraison_jours": 7,
                "periode_reappro_jours": 30,
                "zone_stockage": ZONE.SECHE,
                "emplacement": "C2",
            },
            {
                "reference": "EXC-003",
                "nom": "Stéarate de magnésium végétal",
                "description": "Lubrifiant pour comprimés et gélules. Grade végétal PEV.",
                "categorie": MP.EXCIPIENT,
                "unite": unites["kg"],
                "fournisseur_principal": F2,
                "prix_unitaire": Decimal("120.00"),
                "stock_actuel": Decimal("95.000"),
                "stock_minimum": Decimal("30.000"),
                "stock_maximum": Decimal("200.000"),
                "stock_securite": Decimal("20.000"),
                "methode_approvisionnement": METHODE.POINT_COMMANDE,
                "point_commande": Decimal("40.000"),
                "qec": Decimal("80.000"),
                "delai_livraison_jours": 10,
                "zone_stockage": ZONE.SECHE,
                "emplacement": "C3",
            },
            # Conditionnements
            {
                "reference": "COND-001",
                "nom": "Flacons HDPE 60 mL bouchon sécurité enfant",
                "description": "Flacon polyéthylène haute densité avec dessiccant intégré. Conforme ISO 8317.",
                "categorie": MP.CONDITIONNEMENT,
                "unite": unites["u"],
                "fournisseur_principal": F3,
                "prix_unitaire": Decimal("3.50"),
                "stock_actuel": Decimal("12000.000"),
                "stock_minimum": Decimal("5000.000"),
                "stock_maximum": Decimal("50000.000"),
                "stock_securite": Decimal("3000.000"),
                "methode_approvisionnement": METHODE.REAPPRO_FIXE,
                "qec": Decimal("20000.000"),
                "delai_livraison_jours": 10,
                "periode_reappro_jours": 60,
                "zone_stockage": ZONE.TEMPEREE,
                "emplacement": "D1",
            },
            {
                "reference": "COND-002",
                "nom": "Aluminium feuille blister 20 µm",
                "description": "Aluminium HS (Heat Seal) pour blistéreuse automatique. Largeur 130 mm.",
                "categorie": MP.CONDITIONNEMENT,
                "unite": unites["kg"],
                "fournisseur_principal": F3,
                "prix_unitaire": Decimal("220.00"),
                "stock_actuel": Decimal("340.000"),
                "stock_minimum": Decimal("100.000"),
                "stock_maximum": Decimal("800.000"),
                "stock_securite": Decimal("80.000"),
                "methode_approvisionnement": METHODE.RECOMPLETEMENT,
                "qec": Decimal("300.000"),
                "delai_livraison_jours": 12,
                "periode_reappro_jours": 45,
                "zone_stockage": ZONE.TEMPEREE,
                "emplacement": "D2",
            },
        ]

        created_count = 0
        for mp in matieres_data:
            obj, created = MatierePremiere.objects.get_or_create(
                reference=mp["reference"],
                defaults={**mp, "actif": True},
            )
            if created:
                created_count += 1
                self.stdout.write(
                    f"    ✓ [{obj.reference}] {obj.nom[:55]}"
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"    ~ [{obj.reference}] déjà existant, ignoré.")
                )

        # ──────────────────────────────────────
        # RÉSUMÉ
        # ──────────────────────────────────────
        self.stdout.write("\n" + self.style.SUCCESS("=== Résumé ==================================="))
        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(users_data)} utilisateurs traités"))
        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(unites_data)} unités de mesure créées"))
        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(fournisseurs_data)} fournisseurs créés"))
        self.stdout.write(self.style.SUCCESS(f"  ✓ {created_count}/{len(matieres_data)} matières premières créées"))
        self.stdout.write(self.style.SUCCESS("\n  Identifiants de connexion :"))
        self.stdout.write(self.style.SUCCESS("    admin        /  admin123   (Administrateur)"))
        self.stdout.write(self.style.SUCCESS("    gestionnaire /  gest123    (Responsable Stock)"))
        self.stdout.write(self.style.SUCCESS("    acheteur     /  achat123   (Acheteur)"))
        self.stdout.write(self.style.SUCCESS("\n  Serveur : python manage.py runserver → http://127.0.0.1:8000/\n"))
