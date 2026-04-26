import os
import sys
import django
import random
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockpro.settings')
django.setup()

from produits.models import MatierePremiere, ProduitFini
from mouvements.models import MouvementStock
from core.models import Utilisateur

def seed_movements():
    admin = Utilisateur.objects.filter(is_superuser=True).first()
    matieres = list(MatierePremiere.objects.all())
    produits = list(ProduitFini.objects.all())
    
    now = timezone.now()
    
    print("Génération de mouvements...")
    for i in range(50):
        jours_offset = random.randint(0, 30)
        date_mvt = now - timedelta(days=jours_offset)
        
        # 70% MP, 30% PF
        if random.random() < 0.7:
            item = random.choice(matieres)
            m_type = random.choice(['ENTREE', 'SORTIE'])
            qty = Decimal(str(random.randint(5, 50)))
            
            m = MouvementStock.objects.create(
                matiere=item,
                type_mouvement=m_type,
                quantite=qty,
                operateur=admin,
                motif="Demo mouvement automatique"
            )
            MouvementStock.objects.filter(pk=m.pk).update(date_mouvement=date_mvt)
        else:
            item = random.choice(produits)
            m_type = random.choice(['ENTREE', 'SORTIE'])
            qty = Decimal(str(random.randint(10, 100)))
            
            m = MouvementStock.objects.create(
                produit_fini=item,
                type_mouvement=m_type,
                quantite=qty,
                operateur=admin,
                motif="Demo mouvement automatique"
            )
            MouvementStock.objects.filter(pk=m.pk).update(date_mouvement=date_mvt)
            
    print("50 mouvements créés.")

if __name__ == "__main__":
    seed_movements()
