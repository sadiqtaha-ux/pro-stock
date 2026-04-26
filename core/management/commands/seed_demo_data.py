"""
core/management/commands/seed_demo_data.py
Commande de Seed pour l'industrie pharmaceutique — StockPro
Usage : 
  python manage.py seed_demo_data
  python manage.py seed_demo_data --flush-demo
  python manage.py seed_demo_data --flush-demo --keep-admin
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import math
from datetime import timedelta

# Imports des modèles
from core.models import Utilisateur
from produits.models import Fournisseur, UnitesMesure, MatierePremiere, ProduitFini, Nomenclature, LigneNomenclature
from magasin.models import ZoneStockage, Rayon, NiveauRayon, Emplacement, AffectationStock
from mouvements.models import MouvementStock
from approvisionnement.models import BonCommande, PropositionCommande, PlanMRP


class Command(BaseCommand):
    help = "Purge et recrée un jeu de données de démonstration complet pour StockPro."

    def add_arguments(self, parser):
        parser.add_argument("--flush-demo", action="store_true", help="Supprime les données métier existantes avant de régénérer")
        parser.add_argument("--keep-admin", action="store_true", help="Conserve le superutilisateur existant lors de la suppression")
        parser.add_argument("--force", action="store_true", help="Force la réexécution du seed sans demander confirmation")

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n========================================"))
        self.stdout.write(self.style.MIGRATE_HEADING("  StockPro -- Seed Demo Data"))
        self.stdout.write(self.style.MIGRATE_HEADING("========================================\n"))

        if options["flush_demo"]:
            self.stdout.write(self.style.WARNING("[!] Purge des données métier en cours..."))
            
            # Ordre de suppression strict pour respecter les ForeignKeys
            AffectationStock.objects.all().delete()
            MouvementStock.objects.all().delete()
            BonCommande.objects.all().delete()
            PropositionCommande.objects.all().delete()
            PlanMRP.objects.all().delete()
            LigneNomenclature.objects.all().delete()
            Nomenclature.objects.all().delete()
            ProduitFini.objects.all().delete()
            MatierePremiere.objects.all().delete()
            Emplacement.objects.all().delete()
            NiveauRayon.objects.all().delete()
            Rayon.objects.all().delete()
            ZoneStockage.objects.all().delete()
            Fournisseur.objects.all().delete()
            UnitesMesure.objects.all().delete()
            
            if options["keep_admin"]:
                Utilisateur.objects.filter(is_superuser=False).delete()
                self.stdout.write("    - Utilisateurs (Sauf Admin) supprimés.")
            else:
                Utilisateur.objects.all().delete()
                self.stdout.write("    - Tous les Utilisateurs supprimés.")
                
            self.stdout.write(self.style.SUCCESS("  [OK] Données purgées avec succès.\n"))

        # ---------------------------------------------------------
        # 1. UTILISATEURS
        # ---------------------------------------------------------
        self.stdout.write("  [1/9] Création des utilisateurs...")
        users = [
            {"username": "admin", "password": "Admin@2026", "first_name": "Mohammed", "last_name": "Alaoui", "email": "m.alaoui@pharmaplus.ma", "role": "ADMIN", "service": "Direction SI", "is_staff": True, "is_superuser": True},
            {"username": "resp_stock", "password": "Stock@2026", "first_name": "Fatima-Zahra", "last_name": "Bensouda", "email": "fz.bensouda@pharmaplus.ma", "role": "RESPONSABLE_STOCK", "service": "Gestion des Stocks"},
            {"username": "magasinier1", "password": "Mag1@2026", "first_name": "Youssef", "last_name": "Berrada", "email": "y.berrada@pharmaplus.ma", "role": "MAGASINIER", "service": "Magasin MP"},
            {"username": "acheteur", "password": "Achat@2026", "first_name": "Omar", "last_name": "Cherkaoui", "email": "o.cherkaoui@pharmaplus.ma", "role": "ACHETEUR", "service": "Achats"},
        ]
        
        users_crees = 0
        admin_user = None
        for u in users:
            pwd = u.pop("password")
            obj, created = Utilisateur.objects.get_or_create(username=u["username"], defaults={**u, "password": make_password(pwd), "est_actif": True})
            if created: users_crees += 1
            if obj.username == "admin": admin_user = obj
            
        self.stdout.write(f"    [OK] {users_crees} utilisateurs créés.")

        # ---------------------------------------------------------
        # 2. UNITÉS DE MESURE
        # ---------------------------------------------------------
        self.stdout.write("  [2/9] Création des unités de mesure...")
        unites_data = [
            ("Kilogramme", "kg", True), ("Gramme", "g", True), ("Litre", "L", True),
            ("Millilitre", "mL", True), ("Unité", "u", False), ("Boîte", "bt", False),
            ("Millier", "mill.", False), ("Mètre", "m", True)
        ]
        unites = {}
        unites_crees = 0
        for nom, sym, dec in unites_data:
            u, created = UnitesMesure.objects.get_or_create(symbole=sym, defaults={"nom": nom, "autorise_decimales": dec})
            if created: unites_crees += 1
            unites[sym] = u
        self.stdout.write(f"    [OK] {unites_crees} unités créées.")

        # ---------------------------------------------------------
        # 3. FOURNISSEURS
        # ---------------------------------------------------------
        self.stdout.write("  [3/9] Création des fournisseurs...")
        fournisseurs_data = [
            {"nom": "Sanofi Maroc", "contact": "Dir. Com.", "email": "appro@sanofi.ma", "telephone": "+212 5 22 24 80 00", "ville": "Casablanca"},
            {"nom": "ChemInter Maroc", "contact": "R. El Moussaoui", "email": "r.elmoussaoui@cheminter.ma", "telephone": "+212 5 39 32 00 15", "ville": "Tanger"},
            {"nom": "PackPharma", "contact": "N. Tazi", "email": "n.tazi@packpharma.ma", "telephone": "+212 5 22 63 14 00", "ville": "Casablanca"}
        ]
        fournisseurs = {}
        fr_crees = 0
        for f in fournisseurs_data:
            obj, created = Fournisseur.objects.get_or_create(nom=f["nom"], defaults={**f, "actif": True})
            if created: fr_crees += 1
            fournisseurs[f["nom"]] = obj
        self.stdout.write(f"    [OK] {fr_crees} fournisseurs créés.")

        # ---------------------------------------------------------
        # 4. STRUCTURE DU MAGASIN (Zones, Rayons, Niveaux)
        # ---------------------------------------------------------
        self.stdout.write("  [4/9] Création du magasin...")
        z_seche, _ = ZoneStockage.objects.get_or_create(code="Z-SEC", defaults={"nom": "Zone Sèche", "libelle": "Zone MP sèches", "type_zone": "SECHE", "capacite_totale": 5000})
        z_froide, _ = ZoneStockage.objects.get_or_create(code="Z-FRD", defaults={"nom": "Zone Froide", "libelle": "Chambre froide", "type_zone": "FROIDE", "temperature_min": 2, "temperature_max": 8})
        z_pf, _ = ZoneStockage.objects.get_or_create(code="Z-PF", defaults={"nom": "Zone Produits Finis", "libelle": "Zone expédition PF", "type_zone": "PRODUITS_FINIS"})

        r_seche, _ = Rayon.objects.get_or_create(zone=z_seche, code="A1", defaults={"libelle": "Allée Principale", "type_stock": "MATIERE_PREMIERE", "nombre_niveaux": 3})
        r_froide, _ = Rayon.objects.get_or_create(zone=z_froide, code="F1", defaults={"libelle": "Frigo 1", "type_stock": "MATIERE_PREMIERE", "nombre_niveaux": 2})
        r_pf, _ = Rayon.objects.get_or_create(zone=z_pf, code="P1", defaults={"libelle": "Stock PF", "type_stock": "PRODUIT_FINI", "nombre_niveaux": 4})

        n_seche = [NiveauRayon.objects.get_or_create(rayon=r_seche, numero=i, defaults={"capacite_max": 1000})[0] for i in range(1, 4)]
        n_froide = [NiveauRayon.objects.get_or_create(rayon=r_froide, numero=i, defaults={"capacite_max": 500})[0] for i in range(1, 3)]
        n_pf = [NiveauRayon.objects.get_or_create(rayon=r_pf, numero=i, defaults={"capacite_max": 2000})[0] for i in range(1, 5)]

        self.stdout.write("    [OK] Zones et Rayons créés.")

        # ---------------------------------------------------------
        # 5. MATIÈRES PREMIÈRES
        # ---------------------------------------------------------
        self.stdout.write("  [5/9] Création des matières premières...")
        matieres_data = [
            {"reference": "API-001", "nom": "Paracétamol USP grade", "categorie": "PRINCIPE_ACTIF", "unite": unites["kg"], "fournisseur_principal": fournisseurs["Sanofi Maroc"], "prix_unitaire": Decimal("285.00"), "stock_actuel": Decimal("350.00"), "stock_minimum": Decimal("100.00"), "stock_maximum": Decimal("1200.00"), "methode_approvisionnement": "POINT_COMMANDE", "zone_stockage": "SECHE", "emplacement": "A1-N1"},
            {"reference": "EXC-001", "nom": "Amidon de maïs", "categorie": "EXCIPIENT", "unite": unites["kg"], "fournisseur_principal": fournisseurs["ChemInter Maroc"], "prix_unitaire": Decimal("42.00"), "stock_actuel": Decimal("800.00"), "stock_minimum": Decimal("200.00"), "stock_maximum": Decimal("3000.00"), "methode_approvisionnement": "REAPPRO_FIXE", "zone_stockage": "SECHE", "emplacement": "A1-N2"},
            {"reference": "COND-001", "nom": "Boîtes carton standard", "categorie": "CONDITIONNEMENT", "unite": unites["mill."], "fournisseur_principal": fournisseurs["PackPharma"], "prix_unitaire": Decimal("2.80"), "stock_actuel": Decimal("90.00"), "stock_minimum": Decimal("25.00"), "stock_maximum": Decimal("500.00"), "methode_approvisionnement": "MRP", "zone_stockage": "SECHE", "emplacement": "A1-N3"},
        ]
        matieres = {}
        mp_crees = 0
        for mp in matieres_data:
            obj, created = MatierePremiere.objects.get_or_create(reference=mp["reference"], defaults={**mp})
            if created: mp_crees += 1
            matieres[mp["reference"]] = obj
        self.stdout.write(f"    [OK] {mp_crees} matières premières créées.")

        # ---------------------------------------------------------
        # 6. PRODUITS FINIS & NOMENCLATURES
        # ---------------------------------------------------------
        self.stdout.write("  [6/9] Création des produits finis et nomenclatures...")
        pf_data = [
            {"reference": "PF-PARA-500", "nom": "Doliprane 500mg Boîte de 16", "categorie": "MEDICAMENT", "statut": "DISPONIBLE", "unite": unites["bt"], "stock_actuel": Decimal("1500"), "stock_minimum": Decimal("500"), "stock_maximum": Decimal("5000"), "prix_unitaire": Decimal("15.50"), "zone_stockage": "TEMPEREE", "emplacement": "P1-N1"}
        ]
        produits = {}
        pf_crees = 0
        for pf in pf_data:
            obj, created = ProduitFini.objects.get_or_create(reference=pf["reference"], defaults={**pf})
            if created: pf_crees += 1
            produits[pf["reference"]] = obj

        # Nomenclatures
        nom_para, created_nom = Nomenclature.objects.get_or_create(produit_fini=produits["PF-PARA-500"], defaults={"nom": "Nomenclature Doliprane 500mg B/16", "version": "V1"})
        
        # Lignes
        LigneNomenclature.objects.get_or_create(nomenclature=nom_para, matiere=matieres["API-001"], defaults={"quantite_par_unite": Decimal("0.008")}) # 8g pour 16 cps de 500mg
        LigneNomenclature.objects.get_or_create(nomenclature=nom_para, matiere=matieres["EXC-001"], defaults={"quantite_par_unite": Decimal("0.002")})
        LigneNomenclature.objects.get_or_create(nomenclature=nom_para, matiere=matieres["COND-001"], defaults={"quantite_par_unite": Decimal("0.001")}) # 1 boite = 0.001 millier
        
        self.stdout.write(f"    [OK] {pf_crees} produits finis créés.")

        # ---------------------------------------------------------
        # 7. AFFECTATIONS & MOUVEMENTS (Stock History)
        # ---------------------------------------------------------
        self.stdout.write("  [7/9] Création des historiques de stock et affectations...")
        # Affecter la MP au rayon
        AffectationStock.objects.get_or_create(niveau=n_seche[0], matiere_premiere=matieres["API-001"], defaults={"quantite_affectee": Decimal("350.00")})
        AffectationStock.objects.get_or_create(niveau=n_pf[0], produit_fini=produits["PF-PARA-500"], defaults={"quantite_affectee": Decimal("1500.00")})

        # Créer quelques mouvements d'entrée initiaux (historique)
        MouvementStock.objects.get_or_create(
            matiere=matieres["API-001"], 
            type_mouvement="ENTREE", 
            quantite=Decimal("350.00"),
            defaults={"quantite_avant": Decimal("0"), "quantite_apres": Decimal("350.00"), "motif": "Stock Initial", "operateur": admin_user}
        )
        self.stdout.write("    [OK] Affectations et mouvements créés.")

        # ---------------------------------------------------------
        # 8. APPROVISIONNEMENT (Bons & Propositions)
        # ---------------------------------------------------------
        self.stdout.write("  [8/9] Création de l'approvisionnement...")
        
        PropositionCommande.objects.get_or_create(
            matiere=matieres["API-001"],
            statut="VALIDEE",
            methode="POINT_COMMANDE",
            defaults={"quantite_proposee": Decimal("200.00"), "quantite_validee": Decimal("200.00"), "fournisseur": fournisseurs["Sanofi Maroc"]}
        )
        
        # Le champ 'reference' est auto-généré dans .save(), on ne le passe pas en filtre pour get_or_create
        BonCommande.objects.create(
            matiere=matieres["API-001"],
            fournisseur=fournisseurs["Sanofi Maroc"],
            quantite_commandee=Decimal("200.00"), 
            prix_unitaire=Decimal("285.00"), 
            statut="ENVOYE", 
            cree_par=admin_user, 
            date_envoi=timezone.now() - timedelta(days=2)
        )
        self.stdout.write("    [OK] Propositions et Bons de commande créés.")

        # ---------------------------------------------------------
        # 9. FIN DU SEED
        # ---------------------------------------------------------
        self.stdout.write("  [9/9] Vérification finale...")
        self.stdout.write(self.style.SUCCESS(
            "\n========================================\n"
            "  Seed terminé avec succès !\n"
            "========================================\n"
            f"  Utilisateurs créés: {users_crees}\n"
            f"  Unités créées: {unites_crees}\n"
            f"  Fournisseurs créés: {fr_crees}\n"
            f"  Matières Premières créées: {mp_crees}\n"
            f"  Produits Finis créés: {pf_crees}\n"
            "========================================\n"
            "  Pour tester le système : \n"
            "  -> python manage.py runserver\n"
        ))
