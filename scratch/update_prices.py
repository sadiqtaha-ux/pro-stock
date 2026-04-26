import os
import sys
import django
from decimal import Decimal

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockpro.settings')
django.setup()

from produits.models import MatierePremiere, ProduitFini

def update_prices():
    # Mapping des prix réalistes par catégorie/référence
    prices_mp = {
        "MP-API-001": 1500.00,  # Paracetamol
        "MP-API-002": 2800.00,  # Ibuprofene
        "MP-API-003": 1200.00,  # Aspirine
        "MP-API-004": 3500.00,  # Metformine
        "MP-EXC-001": 45.00,    # Lactose
        "MP-EXC-002": 32.00,    # Amidon
        "MP-EXC-003": 85.00,    # Cellulose
        "MP-EXC-004": 120.00,   # Magnesium
        "MP-EXC-005": 15.00,    # Talc
        "MP-SOL-001": 25.00,    # Ethanol
        "MP-SOL-002": 5.00,     # Eau
        "MP-PACK-001": 0.85,    # Blister
        "MP-PACK-002": 1.20,    # Boite
        "MP-PACK-003": 0.15,    # Notice
        "MP-PACK-004": 2.50,    # Flacon
        "MP-PACK-005": 0.40,    # Bouchon
        "MP-PACK-006": 12.00,   # Film
        "MP-COLD-001": 8500.00, # Reactif froid (Cher !)
        "MP-QA-001": 1.50,      # Gants
        "MP-QA-002": 0.50,      # Masques
    }

    print("Mise à jour des prix Matières Premières...")
    for ref, price in prices_mp.items():
        MatierePremiere.objects.filter(reference=ref).update(prix_unitaire=Decimal(str(price)))

    # Fallback pour les MP restantes
    MatierePremiere.objects.filter(prix_unitaire=0).update(prix_unitaire=Decimal("10.00"))

    print("Mise à jour des prix Produits Finis...")
    ProduitFini.objects.filter(reference="PF-PARA-500").update(prix_unitaire=Decimal("25.00"))
    ProduitFini.objects.filter(reference="PF-IBU-400").update(prix_unitaire=Decimal("45.00"))
    ProduitFini.objects.filter(prix_unitaire=0).update(prix_unitaire=Decimal("20.00"))

    print("Mise à jour terminée.")

if __name__ == "__main__":
    update_prices()
