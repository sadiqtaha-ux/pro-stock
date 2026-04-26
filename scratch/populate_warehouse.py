import os
import django
import random
from decimal import Decimal

import sys
from pathlib import Path

# Ajouter le répertoire racine au sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockpro.settings')
django.setup()

from magasin.models import ZoneStockage, Rayon, Emplacement
from produits.models import MatierePremiere, ProduitFini, UnitesMesure

def populate_warehouse():
    print("--- Peuplement du Magasin ---")
    
    # 0. Unités (Recherche souple pour éviter les erreurs d'unicité)
    unite_u = UnitesMesure.objects.filter(symbole="U").first() or UnitesMesure.objects.filter(nom__icontains="Unit").first()
    if not unite_u:
        unite_u = UnitesMesure.objects.create(symbole="U", nom="Unité de base")
        
    unite_kg = UnitesMesure.objects.filter(symbole="kg").first() or UnitesMesure.objects.filter(nom__icontains="Kilo").first()
    if not unite_kg:
        unite_kg = UnitesMesure.objects.create(symbole="kg", nom="Kilogramme")

    # 1. Création des Zones
    zones_data = [
        {"code": "Z-MP", "lib": "Matières Premières", "type": "MP", "color": "#3b82f6", "x": 50, "y": 50, "w": 400, "h": 500},
        {"code": "Z-PF", "lib": "Produits Finis", "type": "PF", "color": "#10b981", "x": 550, "y": 50, "w": 400, "h": 300},
        {"code": "Z-QU", "lib": "Quarantaine", "type": "QUARANTAINE", "color": "#f59e0b", "x": 550, "y": 400, "w": 400, "h": 150},
    ]

    for zd in zones_data:
        z, created = ZoneStockage.objects.update_or_create(
            code=zd["code"],
            defaults={
                "libelle": zd["lib"],
                "type_zone": zd["type"],
                "couleur": zd["color"],
                "position_x": zd["x"],
                "position_y": zd["y"],
                "largeur": zd["w"],
                "hauteur": zd["h"],
            }
        )
        print(f"Zone {z.code} {'créée' if created else 'mise à jour'}")

        # 2. Création des Rayons pour chaque Zone
        if zd["code"] == "Z-MP":
            # 3 Rayons verticaux pour MP
            for i in range(1, 4):
                r_code = f"R{i}"
                r, _ = Rayon.objects.update_or_create(
                    zone=z, code=r_code,
                    defaults={
                        "libelle": f"Rayon MP {i}",
                        "position_x": zd["x"] + (i * 100) - 50,
                        "position_y": zd["y"] + 50,
                        "largeur": 40,
                        "hauteur": 400,
                        "nombre_colonnes": 5,
                        "nombre_niveaux": 4
                    }
                )
                # Création des emplacements
                for col in range(1, 6):
                    for niv in range(1, 5):
                        Emplacement.objects.get_or_create(
                            rayon=r, niveau=niv, colonne=col,
                            defaults={"statut": "LIBRE"}
                        )
        
        elif zd["code"] == "Z-PF":
            # 2 Rayons horizontaux pour PF
            for i in range(1, 3):
                r_code = f"H{i}"
                r, _ = Rayon.objects.update_or_create(
                    zone=z, code=r_code,
                    defaults={
                        "libelle": f"Rack PF {i}",
                        "position_x": zd["x"] + 50,
                        "position_y": zd["y"] + (i * 100) - 50,
                        "largeur": 300,
                        "hauteur": 40,
                        "orientation": "H",
                        "nombre_colonnes": 8,
                        "nombre_niveaux": 3
                    }
                )
                for col in range(1, 9):
                    for niv in range(1, 4):
                        Emplacement.objects.get_or_create(
                            rayon=r, niveau=niv, colonne=col,
                            defaults={"statut": "LIBRE"}
                        )

    # 3. Création d'articles de test
    print("--- Peuplement des Articles ---")
    
    # MP 1: Normale
    MatierePremiere.objects.update_or_create(
        reference="MP-DEMO-01",
        defaults={
            "nom": "Paracétamol Pur",
            "stock_actuel": 500, "stock_minimum": 100, "stock_maximum": 1000,
            "emplacement": "Z-MP-R1-N01-C01", "unite": unite_kg, "actif": True
        }
    )
    # MP 2: Rupture
    MatierePremiere.objects.update_or_create(
        reference="MP-DEMO-02",
        defaults={
            "nom": "Solvant Ethanol",
            "stock_actuel": 0, "stock_minimum": 50, "stock_maximum": 200,
            "emplacement": "Z-MP-R1-N01-C02", "unite": unite_kg, "actif": True
        }
    )
    # MP 3: Alerte
    MatierePremiere.objects.update_or_create(
        reference="MP-DEMO-03",
        defaults={
            "nom": "Capsules Gélatine",
            "stock_actuel": 45, "stock_minimum": 100, "stock_maximum": 500,
            "point_commande": 150,
            "emplacement": "Z-MP-R2-N01-C01", "unite": unite_u, "actif": True
        }
    )

    # PF 1: Normal
    ProduitFini.objects.update_or_create(
        reference="PF-DEMO-01",
        defaults={
            "nom": "Doliprane 500mg (Boite 16)",
            "stock_actuel": 1200, "stock_minimum": 200, "stock_maximum": 2000,
            "emplacement": "Z-PF-H1-N01-C01", "unite": unite_u, "actif": True
        }
    )
    
    print("Fin du peuplement.")

if __name__ == "__main__":
    populate_warehouse()
