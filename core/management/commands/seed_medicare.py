"""
core/management/commands/seed_medicare.py
Seed réaliste pour l'industrie pharmaceutique — PharmaPlus Maroc
Usage : python manage.py seed_medicare
        python manage.py seed_medicare --reset
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from decimal import Decimal
import math


class Command(BaseCommand):
    help = "Seed réaliste — industrie pharmaceutique PharmaPlus Maroc"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Efface les données existantes avant de régénérer")

    @transaction.atomic
    def handle(self, *args, **options):
        from core.models import Utilisateur
        from produits.models import Fournisseur, UnitesMesure, MatierePremiere

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n========================================\n"
            "  PharmaPlus Maroc -- Seed Pharma\n"
            "========================================\n"
        ))

        # --------------------------------------
        # 0. RESET
        # --------------------------------------
        if options["reset"]:
            MatierePremiere.objects.all().delete()
            Fournisseur.objects.all().delete()
            UnitesMesure.objects.all().delete()
            Utilisateur.objects.filter(
                username__in=["admin", "resp_stock", "magasinier1",
                              "magasinier2", "acheteur", "consultant"]
            ).delete()
            self.stdout.write(self.style.WARNING("  [OK] Donnees existantes supprimees\n"))

        # --------------------------------------
        # 1. UTILISATEURS — 6 profils réalistes
        # --------------------------------------
        self.stdout.write("  [1/5] Creation des utilisateurs...")

        users = [
            {
                "username": "admin",
                "password": "Admin@2026",
                "first_name": "Mohammed",
                "last_name": "Alaoui",
                "email": "m.alaoui@pharmaplus.ma",
                "role": "ADMIN",
                "service": "Direction des Systèmes d'Information",
                "telephone": "+212 6 61 00 00 01",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "resp_stock",
                "password": "Stock@2026",
                "first_name": "Fatima-Zahra",
                "last_name": "Bensouda",
                "email": "fz.bensouda@pharmaplus.ma",
                "role": "RESPONSABLE_STOCK",
                "service": "Gestion des Stocks & Logistique",
                "telephone": "+212 6 61 00 00 02",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "magasinier1",
                "password": "Mag1@2026",
                "first_name": "Youssef",
                "last_name": "Berrada",
                "email": "y.berrada@pharmaplus.ma",
                "role": "MAGASINIER",
                "service": "Magasin Matières Premières",
                "telephone": "+212 6 61 00 00 03",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "magasinier2",
                "password": "Mag2@2026",
                "first_name": "Aicha",
                "last_name": "Tahiri",
                "email": "a.tahiri@pharmaplus.ma",
                "role": "MAGASINIER",
                "service": "Magasin Conditionnement",
                "telephone": "+212 6 61 00 00 04",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "acheteur",
                "password": "Achat@2026",
                "first_name": "Omar",
                "last_name": "Cherkaoui",
                "email": "o.cherkaoui@pharmaplus.ma",
                "role": "ACHETEUR",
                "service": "Approvisionnement & Achats",
                "telephone": "+212 6 61 00 00 05",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "consultant",
                "password": "Consult@2026",
                "first_name": "Sara",
                "last_name": "El Fassi",
                "email": "s.elfassi@pharmaplus.ma",
                "role": "CONSULTANT",
                "service": "Audit Qualité",
                "telephone": "+212 6 61 00 00 06",
                "is_staff": False,
                "is_superuser": False,
            },
        ]

        for u in users:
            pwd = u.pop("password")
            obj, created = Utilisateur.objects.get_or_create(
                username=u["username"],
                defaults={**u, "password": make_password(pwd), "est_actif": True},
            )
            status = "cree" if created else "existant"
            self.stdout.write(
                f"    {'[OK]' if created else '~'} {obj.username:15} "
                f"({obj.get_role_display()}) -- {status}"
            )

        # --------------------------------------
        # 2. UNITÉS DE MESURE — standards pharma
        # --------------------------------------
        self.stdout.write("\n  [2/5] Creation des unites de mesure...")

        unites_data = [
            ("Kilogramme",   "kg"),
            ("Gramme",       "g"),
            ("Milligramme",  "mg"),
            ("Litre",        "L"),
            ("Millilitre",   "mL"),
            ("Unité",        "u"),
            ("Millier",      "mill."),
            ("Mètre",        "m"),
            ("Kilogramme/m²","kg/m²"),
        ]
        unites = {}
        for nom, sym in unites_data:
            u, _ = UnitesMesure.objects.get_or_create(
                nom=nom, defaults={"symbole": sym}
            )
            unites[sym] = u
        self.stdout.write(
            f"    [OK] {len(unites_data)} unites creees"
        )

        # --------------------------------------
        # 3. FOURNISSEURS — réels + Maroc
        # --------------------------------------
        self.stdout.write("\n  [3/5] Creation des fournisseurs...")

        fournisseurs_data = [
            {
                "nom": "Sanofi Maroc",
                "contact": "Direction Commerciale",
                "email": "approvisionnement@sanofi.ma",
                "telephone": "+212 5 22 24 80 00",
                "adresse": "Route de Rabat, Km 12",
                "ville": "Casablanca",
                "pays": "Maroc",
            },
            {
                "nom": "Pfizer Distribution Maroc",
                "contact": "Service Commandes",
                "email": "orders.morocco@pfizer.com",
                "telephone": "+212 5 37 71 84 00",
                "adresse": "Avenue Annakhil, Hay Riad",
                "ville": "Rabat",
                "pays": "Maroc",
            },
            {
                "nom": "ChemInter Maroc",
                "contact": "Rachid El Moussaoui",
                "email": "r.elmoussaoui@cheminter.ma",
                "telephone": "+212 5 39 32 00 15",
                "adresse": "Zone Industrielle de Gzenaya",
                "ville": "Tanger",
                "pays": "Maroc",
            },
            {
                "nom": "PackPharma Casablanca",
                "contact": "Nadia Tazi",
                "email": "n.tazi@packpharma.ma",
                "telephone": "+212 5 22 63 14 00",
                "adresse": "Quartier Industriel Sidi Bernoussi",
                "ville": "Casablanca",
                "pays": "Maroc",
            },
            {
                "nom": "EthanolPur SA",
                "contact": "Hassan Ouali",
                "email": "h.ouali@ethanolpur.ma",
                "telephone": "+212 5 23 40 22 10",
                "adresse": "Zone Industrielle de Berrechid",
                "ville": "Settat",
                "pays": "Maroc",
            },
            {
                "nom": "Sigma-Aldrich Maghreb",
                "contact": "Import/Export Dept.",
                "email": "maghreb@sigma-aldrich.com",
                "telephone": "+212 5 22 25 00 00",
                "adresse": "Twin Center, Tour Ouest",
                "ville": "Casablanca",
                "pays": "Maroc",
            },
            {
                "nom": "BASF Pharma Maroc",
                "contact": "Karim Benjelloun",
                "email": "k.benjelloun@basf.ma",
                "telephone": "+212 5 37 56 30 00",
                "adresse": "Avenue Mohammed VI",
                "ville": "Rabat",
                "pays": "Maroc",
            },
            {
                "nom": "Clariant Chemicals Maroc",
                "contact": "Leila Benali",
                "email": "l.benali@clariant.ma",
                "telephone": "+212 5 37 71 90 00",
                "adresse": "Zone Franche de Kénitra",
                "ville": "Kénitra",
                "pays": "Maroc",
            },
        ]

        fournisseurs = {}
        for f in fournisseurs_data:
            obj, created = Fournisseur.objects.get_or_create(
                nom=f["nom"], defaults={**f, "actif": True}
            )
            fournisseurs[f["nom"]] = obj
            self.stdout.write(
                f"    {'[OK]' if created else '~'} {obj.nom}"
            )

        # --------------------------------------
        # 4. MATIÈRES PREMIÈRES — 20 références
        # --------------------------------------
        self.stdout.write("\n  [4/5] Creation des matieres premieres...")

        MP  = MatierePremiere.Categorie
        M   = MatierePremiere.MethodeApprovisionnement
        Z   = MatierePremiere.ZoneStockage
        F   = fournisseurs
        U   = unites

        # Helper Wilson
        def eoq(D, S, H):
            return round(math.sqrt(2 * D * S / H), 0) if H > 0 else 0

        def pt(D, L, SS):
            return round((D / 365) * L + SS, 0)

        matieres = [

            # ── PRINCIPES ACTIFS ──────────────────────────────────────
            {
                "reference": "API-001",
                "nom": "Paracétamol (Acétaminophène) USP grade",
                "description": (
                    "Principe actif analgésique et antipyrétique. Conforme "
                    "Pharmacopée Européenne 10e éd. et USP 45. Pureté ≥ 99,5 %. "
                    "Stockage : zone sèche, T° < 25 °C, protéger de l'humidité."
                ),
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": U["kg"],
                "fournisseur_principal": F["Sanofi Maroc"],
                "prix_unitaire": Decimal("285.00"),
                "stock_actuel": Decimal("350.000"),
                "stock_minimum": Decimal("100.000"),
                "stock_maximum": Decimal("1200.000"),
                "stock_securite": Decimal("80.000"),
                "methode_approvisionnement": M.POINT_COMMANDE,
                "point_commande": Decimal(str(pt(4800, 7, 80))),
                "qec": Decimal(str(eoq(4800, 450, 75))),
                "delai_livraison_jours": 7,
                "zone_stockage": Z.SECHE,
                "emplacement": "A-01",
            },
            {
                "reference": "API-002",
                "nom": "Amoxicilline Trihydrate Ph. Eur.",
                "description": (
                    "Antibiotique semi-synthétique de la famille des aminopénicillines. "
                    "Grade pharmaceutique conforme Ph. Eur. Pureté ≥ 98,5 %. "
                    "Stockage : zone sèche, T° 15–25 °C. Sensible à l'humidité."
                ),
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": U["kg"],
                "fournisseur_principal": F["Pfizer Distribution Maroc"],
                "prix_unitaire": Decimal("1850.00"),
                "stock_actuel": Decimal("150.000"),
                "stock_minimum": Decimal("50.000"),
                "stock_maximum": Decimal("500.000"),
                "stock_securite": Decimal("40.000"),
                "methode_approvisionnement": M.POINT_COMMANDE,
                "point_commande": Decimal(str(pt(1800, 10, 40))),
                "qec": Decimal(str(eoq(1800, 380, 110))),
                "delai_livraison_jours": 10,
                "zone_stockage": Z.SECHE,
                "emplacement": "A-02",
            },
            {
                "reference": "API-003",
                "nom": "Ibuprofène micronisé BP grade",
                "description": (
                    "AINS de la famille des propionates. Grade pharmaceutique BP/Ph. Eur. "
                    "Particules micronisées D90 < 50 µm pour compression directe. "
                    "T° stockage : 15–25 °C."
                ),
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": U["kg"],
                "fournisseur_principal": F["Sigma-Aldrich Maghreb"],
                "prix_unitaire": Decimal("490.00"),
                "stock_actuel": Decimal("95.000"),
                "stock_minimum": Decimal("60.000"),
                "stock_maximum": Decimal("400.000"),
                "stock_securite": Decimal("40.000"),
                "methode_approvisionnement": M.REAPPRO_FIXE,
                "point_commande": Decimal("80.000"),
                "qec": Decimal(str(eoq(2400, 400, 60))),
                "delai_livraison_jours": 14,
                "periode_reappro_jours": 30,
                "zone_stockage": Z.SECHE,
                "emplacement": "A-03",
            },
            {
                "reference": "API-004",
                "nom": "Métformine Chlorhydrate Ph. Eur.",
                "description": (
                    "Antidiabétique oral, classe des biguanides. Conforme Ph. Eur. 10. "
                    "Pureté ≥ 99,0 %. Hygroscopique — stockage en récipient hermétique."
                ),
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": U["kg"],
                "fournisseur_principal": F["BASF Pharma Maroc"],
                "prix_unitaire": Decimal("275.00"),
                "stock_actuel": Decimal("0.000"),   # Rupture simulée
                "stock_minimum": Decimal("50.000"),
                "stock_maximum": Decimal("350.000"),
                "stock_securite": Decimal("35.000"),
                "methode_approvisionnement": M.POINT_COMMANDE,
                "point_commande": Decimal(str(pt(2400, 18, 35))),
                "qec": Decimal(str(eoq(2400, 300, 50))),
                "delai_livraison_jours": 18,
                "zone_stockage": Z.SECHE,
                "emplacement": "A-04",
            },
            {
                "reference": "API-005",
                "nom": "Atorvastatine Calcique amorphe",
                "description": (
                    "Statine hypolipidémiante 3e génération. Pureté ≥ 99,5 %. "
                    "Forme amorphe — biodisponibilité optimisée. "
                    "Sensible lumière et humidité. Conserver à l'abri."
                ),
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": U["kg"],
                "fournisseur_principal": F["Pfizer Distribution Maroc"],
                "prix_unitaire": Decimal("8500.00"),
                "stock_actuel": Decimal("12.500"),
                "stock_minimum": Decimal("10.000"),
                "stock_maximum": Decimal("60.000"),
                "stock_securite": Decimal("8.000"),
                "methode_approvisionnement": M.MRP,
                "qec": Decimal("25.000"),
                "delai_livraison_jours": 30,
                "taux_rebut": Decimal("0.0200"),
                "zone_stockage": Z.SECHE,
                "emplacement": "A-05",
            },
            {
                "reference": "API-006",
                "nom": "Oméprazole poudre micronisée",
                "description": (
                    "Inhibiteur de la pompe à protons. Grade pharmaceutique Ph. Eur. "
                    "Sensible à la chaleur et à l'humidité. "
                    "Stockage à T° < 25 °C, HR < 40 %."
                ),
                "categorie": MP.PRINCIPE_ACTIF,
                "unite": U["kg"],
                "fournisseur_principal": F["Sigma-Aldrich Maghreb"],
                "prix_unitaire": Decimal("3200.00"),
                "stock_actuel": Decimal("8.000"),
                "stock_minimum": Decimal("15.000"),    # Alerte simulée
                "stock_maximum": Decimal("80.000"),
                "stock_securite": Decimal("10.000"),
                "methode_approvisionnement": M.POINT_COMMANDE,
                "point_commande": Decimal("18.000"),
                "qec": Decimal("35.000"),
                "delai_livraison_jours": 21,
                "zone_stockage": Z.SECHE,
                "emplacement": "A-06",
            },

            # ── EXCIPIENTS ────────────────────────────────────────────
            {
                "reference": "EXC-001",
                "nom": "Amidon de maïs prégélatinisé Ph. Eur.",
                "description": (
                    "Liant et désintégrant pharmaceutique. Grade Ph. Eur. / USP-NF. "
                    "Conforme GRAS FDA. Stockage T° 15–25 °C, HR < 60 %."
                ),
                "categorie": MP.EXCIPIENT,
                "unite": U["kg"],
                "fournisseur_principal": F["ChemInter Maroc"],
                "prix_unitaire": Decimal("42.00"),
                "stock_actuel": Decimal("800.000"),
                "stock_minimum": Decimal("200.000"),
                "stock_maximum": Decimal("3000.000"),
                "stock_securite": Decimal("150.000"),
                "methode_approvisionnement": M.REAPPRO_FIXE,
                "point_commande": Decimal("350.000"),
                "qec": Decimal(str(eoq(7200, 260, 28))),
                "delai_livraison_jours": 5,
                "periode_reappro_jours": 21,
                "zone_stockage": Z.SECHE,
                "emplacement": "B-01",
            },
            {
                "reference": "EXC-002",
                "nom": "Cellulose Microcristalline (MCC) PH-102",
                "description": (
                    "Excipient de compression directe. Grade Ph. Eur./USP-NF. "
                    "Diamètre moyen particule : 100 µm. Excellent liant et délitant. "
                    "T° stockage : ambiante, protéger humidité."
                ),
                "categorie": MP.EXCIPIENT,
                "unite": U["kg"],
                "fournisseur_principal": F["Clariant Chemicals Maroc"],
                "prix_unitaire": Decimal("85.00"),
                "stock_actuel": Decimal("520.000"),
                "stock_minimum": Decimal("150.000"),
                "stock_maximum": Decimal("1000.000"),
                "stock_securite": Decimal("100.000"),
                "methode_approvisionnement": M.RECOMPLETEMENT,
                "point_commande": Decimal("200.000"),
                "qec": Decimal("400.000"),
                "delai_livraison_jours": 7,
                "periode_reappro_jours": 30,
                "zone_stockage": Z.SECHE,
                "emplacement": "B-02",
            },
            {
                "reference": "EXC-003",
                "nom": "Stéarate de magnésium végétal Ph. Eur.",
                "description": (
                    "Lubrifiant pour comprimés et gélules. Origine végétale (palme). "
                    "Grade PEV (Pureté Élevée Végétal). Conforme Ph. Eur. "
                    "Teneur en acide stéarique ≥ 40 %."
                ),
                "categorie": MP.EXCIPIENT,
                "unite": U["kg"],
                "fournisseur_principal": F["BASF Pharma Maroc"],
                "prix_unitaire": Decimal("120.00"),
                "stock_actuel": Decimal("95.000"),
                "stock_minimum": Decimal("30.000"),
                "stock_maximum": Decimal("200.000"),
                "stock_securite": Decimal("20.000"),
                "methode_approvisionnement": M.POINT_COMMANDE,
                "point_commande": Decimal("40.000"),
                "qec": Decimal(str(eoq(600, 200, 20))),
                "delai_livraison_jours": 10,
                "zone_stockage": Z.SECHE,
                "emplacement": "B-03",
            },
            {
                "reference": "EXC-004",
                "nom": "Hydroxypropylcellulose (HPC) LF grade",
                "description": (
                    "Liant hydrosoluble pour granulation humide et pelliculage. "
                    "Grade LF (Low Flocculation). Conforme Ph. Eur./USP-NF. "
                    "Viscosité 2% : 75–150 mPa·s."
                ),
                "categorie": MP.EXCIPIENT,
                "unite": U["kg"],
                "fournisseur_principal": F["Clariant Chemicals Maroc"],
                "prix_unitaire": Decimal("310.00"),
                "stock_actuel": Decimal("45.000"),
                "stock_minimum": Decimal("20.000"),
                "stock_maximum": Decimal("150.000"),
                "stock_securite": Decimal("15.000"),
                "methode_approvisionnement": M.RECOMPLETEMENT,
                "point_commande": Decimal("25.000"),
                "qec": Decimal("60.000"),
                "delai_livraison_jours": 14,
                "periode_reappro_jours": 45,
                "zone_stockage": Z.SECHE,
                "emplacement": "B-04",
            },
            {
                "reference": "EXC-005",
                "nom": "Talc pharmaceutique USP",
                "description": (
                    "Lubrifiant et anti-adhérent pour formes solides. Grade USP/Ph. Eur. "
                    "Teneur en magnésium silicate hydraté ≥ 99,0 %. "
                    "Granulométrie D90 < 45 µm."
                ),
                "categorie": MP.EXCIPIENT,
                "unite": U["kg"],
                "fournisseur_principal": F["ChemInter Maroc"],
                "prix_unitaire": Decimal("28.00"),
                "stock_actuel": Decimal("280.000"),
                "stock_minimum": Decimal("50.000"),
                "stock_maximum": Decimal("500.000"),
                "stock_securite": Decimal("40.000"),
                "methode_approvisionnement": M.REAPPRO_FIXE,
                "point_commande": Decimal("80.000"),
                "qec": Decimal("180.000"),
                "delai_livraison_jours": 5,
                "periode_reappro_jours": 60,
                "zone_stockage": Z.SECHE,
                "emplacement": "B-05",
            },
            {
                "reference": "EXC-006",
                "nom": "Éthanol 96% (alcool éthylique) Ph. Eur.",
                "description": (
                    "Solvant de granulation et nettoyage. Grade Pharmacopée Européenne. "
                    "Teneur éthanol : 95,1–96,9 % v/v. "
                    "Produit inflammable — stockage zone sécurisée ventilée."
                ),
                "categorie": MP.EXCIPIENT,
                "unite": U["L"],
                "fournisseur_principal": F["EthanolPur SA"],
                "prix_unitaire": Decimal("18.50"),
                "stock_actuel": Decimal("500.000"),
                "stock_minimum": Decimal("100.000"),
                "stock_maximum": Decimal("2000.000"),
                "stock_securite": Decimal("80.000"),
                "methode_approvisionnement": M.POINT_COMMANDE,
                "point_commande": Decimal(str(pt(2400, 4, 80))),
                "qec": Decimal(str(eoq(2400, 200, 45))),
                "delai_livraison_jours": 4,
                "zone_stockage": Z.SECHE,
                "emplacement": "B-06",
            },
            {
                "reference": "EXC-007",
                "nom": "Eau purifiée pour préparations injectables",
                "description": (
                    "Eau HPW (Highly Purified Water) — Ph. Eur. Conductivité < 1.1 µS/cm. "
                    "TOC < 0.5 mg/L. Usage : solvant sirop et formes liquides. "
                    "Produite sur site — renouvellement hebdomadaire."
                ),
                "categorie": MP.EXCIPIENT,
                "unite": U["L"],
                "fournisseur_principal": F["ChemInter Maroc"],
                "prix_unitaire": Decimal("2.50"),
                "stock_actuel": Decimal("800.000"),
                "stock_minimum": Decimal("200.000"),
                "stock_maximum": Decimal("2000.000"),
                "stock_securite": Decimal("150.000"),
                "methode_approvisionnement": M.REAPPRO_FIXE,
                "point_commande": Decimal("300.000"),
                "qec": Decimal("1000.000"),
                "delai_livraison_jours": 2,
                "periode_reappro_jours": 7,
                "zone_stockage": Z.TEMPEREE,
                "emplacement": "B-07",
            },

            # ── CONDITIONNEMENT ───────────────────────────────────────
            {
                "reference": "COND-001",
                "nom": "Gélules vides HPMC taille 0 — blanc opaque",
                "description": (
                    "Gélules à deux pièces en Hydroxypropylméthylcellulose. "
                    "Taille 0 — contenance 0.68 mL. Convient végétaliens. "
                    "Conforme Ph. Eur. — Humidité 5–8 %."
                ),
                "categorie": MP.CONDITIONNEMENT,
                "unite": U["mill."],
                "fournisseur_principal": F["PackPharma Casablanca"],
                "prix_unitaire": Decimal("4.20"),
                "stock_actuel": Decimal("120.000"),
                "stock_minimum": Decimal("30.000"),
                "stock_maximum": Decimal("600.000"),
                "stock_securite": Decimal("25.000"),
                "methode_approvisionnement": M.REAPPRO_FIXE,
                "point_commande": Decimal("50.000"),
                "qec": Decimal(str(eoq(480, 320, 2.5))),
                "delai_livraison_jours": 3,
                "periode_reappro_jours": 30,
                "zone_stockage": Z.TEMPEREE,
                "emplacement": "C-01",
            },
            {
                "reference": "COND-002",
                "nom": "Flacons verre brun type III 200 mL",
                "description": (
                    "Flacons en verre borosilicaté brun (protection UV). "
                    "Volume nominal 200 mL — Col 28 mm. "
                    "Conforme ISO 4796 et Ph. Eur. Classe Hydrolytique III."
                ),
                "categorie": MP.CONDITIONNEMENT,
                "unite": U["mill."],
                "fournisseur_principal": F["PackPharma Casablanca"],
                "prix_unitaire": Decimal("8.50"),
                "stock_actuel": Decimal("80.000"),
                "stock_minimum": Decimal("20.000"),
                "stock_maximum": Decimal("400.000"),
                "stock_securite": Decimal("15.000"),
                "methode_approvisionnement": M.REAPPRO_FIXE,
                "point_commande": Decimal("30.000"),
                "qec": Decimal(str(eoq(240, 280, 3.0))),
                "delai_livraison_jours": 5,
                "periode_reappro_jours": 180,
                "zone_stockage": Z.SECHE,
                "emplacement": "C-02",
            },
            {
                "reference": "COND-003",
                "nom": "Film PVC thermoformable 250 µm",
                "description": (
                    "Film PVC rigide pour blistéreuse automatique. "
                    "Épaisseur 250 µm, largeur 130 mm. "
                    "Perméabilité vapeur d'eau : 3 g/m²/24h. Conforme ISO 15223."
                ),
                "categorie": MP.CONDITIONNEMENT,
                "unite": U["m"],
                "fournisseur_principal": F["PackPharma Casablanca"],
                "prix_unitaire": Decimal("0.85"),
                "stock_actuel": Decimal("15000.000"),
                "stock_minimum": Decimal("5000.000"),
                "stock_maximum": Decimal("50000.000"),
                "stock_securite": Decimal("3000.000"),
                "methode_approvisionnement": M.RECOMPLETEMENT,
                "point_commande": Decimal("6000.000"),
                "qec": Decimal("20000.000"),
                "delai_livraison_jours": 7,
                "periode_reappro_jours": 45,
                "zone_stockage": Z.TEMPEREE,
                "emplacement": "C-03",
            },
            {
                "reference": "COND-004",
                "nom": "Aluminium HS 20 µm pour blister",
                "description": (
                    "Feuille aluminium Heat Seal pour operculage blister. "
                    "Épaisseur 20 µm, largeur 130 mm. "
                    "Revêtement thermosoudable acrylique. Barrière vapeur totale."
                ),
                "categorie": MP.CONDITIONNEMENT,
                "unite": U["m"],
                "fournisseur_principal": F["PackPharma Casablanca"],
                "prix_unitaire": Decimal("1.20"),
                "stock_actuel": Decimal("22000.000"),
                "stock_minimum": Decimal("8000.000"),
                "stock_maximum": Decimal("60000.000"),
                "stock_securite": Decimal("5000.000"),
                "methode_approvisionnement": M.RECOMPLETEMENT,
                "point_commande": Decimal("10000.000"),
                "qec": Decimal("25000.000"),
                "delai_livraison_jours": 7,
                "periode_reappro_jours": 45,
                "zone_stockage": Z.TEMPEREE,
                "emplacement": "C-04",
            },
            {
                "reference": "COND-005",
                "nom": "Étiquettes adhésives autocollantes",
                "description": (
                    "Étiquettes en papier couché blanc brillant. "
                    "Format 70x50 mm, adhésif permanent acrylique. "
                    "Résistance humidité. Impression offset quadrichromie."
                ),
                "categorie": MP.CONDITIONNEMENT,
                "unite": U["mill."],
                "fournisseur_principal": F["PackPharma Casablanca"],
                "prix_unitaire": Decimal("1.50"),
                "stock_actuel": Decimal("200.000"),
                "stock_minimum": Decimal("50.000"),
                "stock_maximum": Decimal("1000.000"),
                "stock_securite": Decimal("40.000"),
                "methode_approvisionnement": M.RECOMPLETEMENT,
                "point_commande": Decimal("48.000"),
                "qec": Decimal("66.000"),
                "delai_livraison_jours": 3,
                "periode_reappro_jours": 7,
                "zone_stockage": Z.SECHE,
                "emplacement": "C-05",
            },
            {
                "reference": "COND-006",
                "nom": "Boîtes carton secondaire — format standard",
                "description": (
                    "Boîtes en carton SBS 350 g/m² — format 90x55x20 mm. "
                    "Impression offset 4 couleurs + vernis mat. "
                    "Conformes Directive 2001/83/CE — notice intégrée."
                ),
                "categorie": MP.CONDITIONNEMENT,
                "unite": U["mill."],
                "fournisseur_principal": F["PackPharma Casablanca"],
                "prix_unitaire": Decimal("2.80"),
                "stock_actuel": Decimal("90.000"),
                "stock_minimum": Decimal("25.000"),
                "stock_maximum": Decimal("500.000"),
                "stock_securite": Decimal("20.000"),
                "methode_approvisionnement": M.REAPPRO_FIXE,
                "point_commande": Decimal("40.000"),
                "qec": Decimal(str(eoq(720, 190, 2.0))),
                "delai_livraison_jours": 3,
                "periode_reappro_jours": 91,
                "zone_stockage": Z.SECHE,
                "emplacement": "C-06",
            },
            {
                "reference": "COND-007",
                "nom": "Notices d'utilisation — lot mixte produits",
                "description": (
                    "Notices en papier bible 40 g/m² — impression recto-verso. "
                    "Format plié 100x70 mm (ouvert 200x280 mm). "
                    "Conformes AMM et Directive 2001/83/CE."
                ),
                "categorie": MP.CONDITIONNEMENT,
                "unite": U["mill."],
                "fournisseur_principal": F["PackPharma Casablanca"],
                "prix_unitaire": Decimal("0.95"),
                "stock_actuel": Decimal("180.000"),
                "stock_minimum": Decimal("50.000"),
                "stock_maximum": Decimal("800.000"),
                "stock_securite": Decimal("40.000"),
                "methode_approvisionnement": M.MRP,
                "qec": Decimal("300.000"),
                "delai_livraison_jours": 5,
                "taux_rebut": Decimal("0.0100"),
                "zone_stockage": Z.SECHE,
                "emplacement": "C-07",
            },
        ]

        created_count = 0
        for mp_data in matieres:
            mp_data.setdefault("taux_rebut", Decimal("0.0000"))
            mp_data.setdefault("periode_reappro_jours", 30)
            obj, created = MatierePremiere.objects.get_or_create(
                reference=mp_data["reference"],
                defaults={**mp_data, "actif": True},
            )
            if created:
                created_count += 1
                status_icon = "[OK]"
                pct = float(obj.stock_actuel / obj.stock_maximum * 100) if obj.stock_maximum else 0
                alerte = " [RUPTURE]" if obj.stock_actuel <= 0 else (
                         " [ALERTE]"  if obj.stock_actuel <= obj.stock_minimum else "")
                self.stdout.write(
                    f"    [OK] [{obj.reference}] {obj.nom[:45]:<45} "
                    f"{pct:5.1f}%{alerte}"
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"    ~ [{obj.reference}] deja existant -- ignore"
                    )
                )

        # --------------------------------------
        # 5. RÉSUMÉ
        # --------------------------------------
        self.stdout.write(
            self.style.SUCCESS(
                f"\n========================================"
                f"\n  Seed termine avec succes"
                f"\n========================================"
                f"\n  Utilisateurs  : {len(users):<5}"
                f"\n  Fournisseurs  : {len(fournisseurs_data):<5}"
                f"\n  Matieres      : {created_count}/{len(matieres):<3}"
                f"\n========================================"
                f"\n  IDENTIFIANTS DE CONNEXION"
                f"\n  admin       / Admin@2026"
                f"\n  resp_stock  / Stock@2026"
                f"\n  magasinier1 / Mag1@2026"
                f"\n  acheteur    / Achat@2026"
                f"\n  consultant  / Consult@2026"
                f"\n========================================"
                f"\n  ETATS SIMULES"
                f"\n  API-004 Metformine   -> RUPTURE"
                f"\n  API-006 Omeprazole   -> ALERTE"
                f"\n========================================\n"
            )
        )
