import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockpro.settings')
django.setup()

from magasin.models import ZoneStockage, Rayon, NiveauRayon
from django.db import transaction

def optimize():
    with transaction.atomic():
        # 1. Mise à jour des Zones (Dimensions et Positions)
        # Disposition : Colonne Gauche (Réception/Quarantaine), Centre (Stockage principal), Droite (Sortie/PF)
        
        zones_config = {
            "Z-REC": {"x": 50,  "y": 50,  "w": 350, "h": 500, "color": "#f1f5f9", "name": "Zone de Réception"},
            "Z-QU":  {"x": 50,  "y": 600, "w": 350, "h": 500, "color": "#fef9c3", "name": "Quarantaine"},
            "Z-MP":  {"x": 450, "y": 50,  "w": 1050, "h": 700, "color": "#dbeafe", "name": "Matières Premières (Ambiante)"},
            "Z-FR":  {"x": 450, "y": 800, "w": 500, "h": 300, "color": "#ccfbf1", "name": "Chambre Froide (2-8°C)"},
            "Z-SEC": {"x": 1000, "y": 800, "w": 500, "h": 300, "color": "#fde68a", "name": "Zone Sèche / Sensible"},
            "Z-PF":  {"x": 1550, "y": 50,  "w": 400, "h": 1050, "color": "#dcfce7", "name": "Produits Finis / Expédition"},
        }

        for code, cfg in zones_config.items():
            zone, created = ZoneStockage.objects.update_or_create(
                code=code,
                defaults={
                    "nom": cfg["name"],
                    "libelle": cfg["name"],
                    "position_x": cfg["x"],
                    "position_y": cfg["y"],
                    "largeur": cfg["w"],
                    "hauteur": cfg["h"],
                    "couleur": cfg["color"],
                    "actif": True
                }
            )

        # 2. Réorganisation des Rayons (Racks)
        # Dans Z-MP (Matières Premières) : On crée des allées verticales
        z_mp = ZoneStockage.objects.get(code="Z-MP")
        # On supprime les anciens rayons de Z-MP pour recréer proprement (attention aux affectations)
        # Pour cet exercice, on va juste repositionner les rayons existants s'ils existent
        
        rayons_mp = list(Rayon.objects.filter(zone=z_mp))
        for i, r in enumerate(rayons_mp):
            # Allées de 120px de large, espacées de 200px
            r.position_x = z_mp.position_x + 50 + (i * 200)
            r.position_y = z_mp.position_y + 100
            r.largeur = 120
            r.hauteur = 500
            r.save()

        # Si on manque de rayons dans Z-MP, on en ajoute
        if len(rayons_mp) < 5:
            for i in range(len(rayons_mp), 5):
                r = Rayon.objects.create(
                    zone=z_mp,
                    code=f"R-MP-{i+1:02d}",
                    nom=f"Rayon MP Allée {i+1}",
                    position_x=z_mp.position_x + 50 + (i * 200),
                    position_y=z_mp.position_y + 100,
                    largeur=120,
                    hauteur=500,
                    nombre_niveaux=5
                )
                for n in range(1, 6):
                    NiveauRayon.objects.create(rayon=r, numero=n, libelle=f"Niveau {n}")

        # Dans Z-PF (Produits Finis) : Allées horizontales
        z_pf = ZoneStockage.objects.get(code="Z-PF")
        rayons_pf = list(Rayon.objects.filter(zone=z_pf))
        for i, r in enumerate(rayons_pf):
            r.position_x = z_pf.position_x + 50
            r.position_y = z_pf.position_y + 50 + (i * 150)
            r.largeur = 300
            r.hauteur = 80
            r.save()
            
        if len(rayons_pf) < 6:
             for i in range(len(rayons_pf), 6):
                r = Rayon.objects.create(
                    zone=z_pf,
                    code=f"R-PF-{i+1:02d}",
                    nom=f"Rayon PF {i+1}",
                    position_x=z_pf.position_x + 50,
                    position_y=z_pf.position_y + 50 + (i * 150),
                    largeur=300,
                    hauteur=80,
                    nombre_niveaux=4
                )
                for n in range(1, 5):
                    NiveauRayon.objects.create(rayon=r, numero=n, libelle=f"Niveau {n}")

        # Zones spécifiques (Un rayon par zone)
        for code_z, code_r in [("Z-FR", "R-FR-01"), ("Z-SEC", "R-SEC-01")]:
            z = ZoneStockage.objects.get(code=code_z)
            r, _ = Rayon.objects.get_or_create(
                code=code_r, zone=z,
                defaults={"nom": f"Rayon {code_z}", "nombre_niveaux": 3}
            )
            r.position_x = z.position_x + 50
            r.position_y = z.position_y + 50
            r.largeur = z.largeur - 100
            r.hauteur = z.hauteur - 100
            r.save()

if __name__ == "__main__":
    optimize()
    print("Disposition du magasin optimisée avec succès.")
