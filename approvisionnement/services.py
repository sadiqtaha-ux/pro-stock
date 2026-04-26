"""
approvisionnement/services.py
Services de calcul pour les 4 méthodes d'approvisionnement
MediCare Industries
"""
import math
from decimal import Decimal
from django.utils import timezone

from produits.models import MatierePremiere
from .models import BonCommande


class PlanificateurService:
    """
    Service central du planificateur d'approvisionnement.
    Analyse les matières selon leur méthode d'approvisionnement et génère des propositions.
    Intègre une logique anti-doublon basée sur cle_deduplication.
    """

    @staticmethod
    def run_planificateur(utilisateur=None):
        import datetime
        from decimal import Decimal
        from django.utils import timezone
        
        # Le statut MANUEL ou MRP n'est pas traité ici (MRP a son propre simulateur, Manuel est... manuel)
        # Mais on peut inclure MRP s'il génère des ruptures globales sans nomenclature spécifique.
        matieres = MatierePremiere.objects.filter(
            actif=True, 
            fournisseur_principal__isnull=False
        )
        
        resultats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }
        
        aujourd_hui = timezone.now().date()
        
        for m in matieres:
            try:
                methode = m.methode_approvisionnement
                qte_proposee = 0
                date_besoin = aujourd_hui
                periode_cle = ""
                
                if methode == MatierePremiere.MethodeApprovisionnement.POINT_COMMANDE:
                    if m.stock_actuel <= m.point_commande:
                        qte_proposee = m.qec if m.qec > 0 else (m.stock_maximum - m.stock_actuel)
                        if qte_proposee <= 0: qte_proposee = m.lot_minimum or 1
                        iso_year, iso_week, _ = aujourd_hui.isocalendar()
                        periode_cle = f"{iso_year}-W{iso_week:02d}"
                    else:
                        continue
                        
                elif methode == MatierePremiere.MethodeApprovisionnement.REAPPRO_FIXE:
                    dernier_bc = BonCommande.objects.filter(
                        matiere=m, 
                        statut__in=[BonCommande.Statut.VALIDEE, BonCommande.Statut.ENVOYE, BonCommande.Statut.CONFIRME]
                    ).order_by('-date_creation').first()
                    
                    if dernier_bc and m.periode_reapprovisionnement:
                        date_prochaine = dernier_bc.date_creation.date() + datetime.timedelta(days=m.periode_reapprovisionnement)
                        if aujourd_hui < date_prochaine:
                            continue
                    
                    qte_proposee = m.qec if m.qec > 0 else (m.stock_maximum - m.stock_actuel)
                    if qte_proposee <= 0: qte_proposee = m.lot_minimum or 1
                    periode_cle = f"{aujourd_hui.year}-{aujourd_hui.month:02d}"
                    
                elif methode == MatierePremiere.MethodeApprovisionnement.RECOMPLETEMENT:
                    qte_proposee = m.stock_maximum - m.stock_actuel
                    # Déduire les commandes en cours ?
                    cmd_en_cours = BonCommande.objects.filter(
                        matiere=m, 
                        statut__in=[BonCommande.Statut.VALIDEE, BonCommande.Statut.ENVOYE, BonCommande.Statut.CONFIRME]
                    ).aggregate(total=models.Sum('quantite_commandee'))['total'] or 0
                    
                    qte_proposee -= Decimal(str(cmd_en_cours))
                    
                    if qte_proposee <= 0:
                        continue
                    periode_cle = f"{aujourd_hui.year}-{aujourd_hui.month:02d}"
                    
                elif methode == MatierePremiere.MethodeApprovisionnement.MRP:
                    # Traitement basique hors-simulateur (pour les ruptures directes sur stock minimum)
                    if m.stock_actuel <= m.stock_minimum:
                        qte_proposee = m.qec if m.qec > 0 else (m.stock_maximum - m.stock_actuel)
                        if qte_proposee <= 0: qte_proposee = m.lot_minimum or 1
                        periode_cle = f"{aujourd_hui.strftime('%Y-%m-%d')}"
                    else:
                        continue
                else:
                    continue
                    
                if qte_proposee <= 0:
                    continue
                    
                # Format de la clé : ID-METHODE-PERIODE
                cle_dedup = f"{m.pk}-{methode}-{periode_cle}"
                
                # Check si un BC existant couvre déjà ce besoin (pour les 15 derniers jours)
                bc_existants = BonCommande.objects.filter(
                    matiere=m, 
                    statut__in=[BonCommande.Statut.BROUILLON, BonCommande.Statut.ENVOYE, BonCommande.Statut.CONFIRME],
                    date_creation__gte=timezone.now() - datetime.timedelta(days=15)
                ).exists()
                
                if bc_existants:
                    resultats["skipped"] += 1
                    continue
                
                from .models import PropositionCommande
                
                # Ignorer si rejeté récemment (7 jours)
                anciennes_rejetees = PropositionCommande.objects.filter(
                    cle_deduplication=cle_dedup,
                    statut=PropositionCommande.Statut.REJETEE,
                    date_generation__gte=timezone.now() - datetime.timedelta(days=7)
                ).exists()
                
                if anciennes_rejetees:
                    resultats["skipped"] += 1
                    continue
                
                # Mettre à jour si en attente, sinon créer
                prop_existante = PropositionCommande.objects.filter(
                    cle_deduplication=cle_dedup,
                    statut=PropositionCommande.Statut.EN_ATTENTE
                ).first()
                
                if prop_existante:
                    nouvelle_qte = Decimal(str(round(qte_proposee, 4)))
                    if prop_existante.quantite_proposee != nouvelle_qte:
                        prop_existante.quantite_proposee = nouvelle_qte
                        prop_existante.detail_calcul["updated_at"] = aujourd_hui.isoformat()
                        prop_existante.save(update_fields=['quantite_proposee', 'detail_calcul'])
                        resultats["updated"] += 1
                    else:
                        resultats["skipped"] += 1
                else:
                    PropositionCommande.objects.create(
                        matiere=m,
                        fournisseur=m.fournisseur_principal,
                        methode=methode,
                        cle_deduplication=cle_dedup,
                        quantite_proposee=Decimal(str(round(qte_proposee, 4))),
                        urgence=(m.stock_actuel <= 0),
                        date_besoin=date_besoin,
                        statut=PropositionCommande.Statut.EN_ATTENTE,
                        detail_calcul={
                            "stock_actuel": float(m.stock_actuel),
                            "point_commande": float(m.point_commande) if m.point_commande else None,
                            "stock_max": float(m.stock_maximum) if m.stock_maximum else None,
                            "generateur": "Planificateur automatique"
                        }
                    )
                    resultats["created"] += 1
                    
            except Exception as e:
                resultats["errors"].append(f"{m.reference}: {str(e)}")
                
        return resultats


class ExplosionBesoinsMRP:
    """
    Service d'explosion de nomenclature (BOM Explosion).
    Calcule les besoins en matières premières pour une production de PF donnée.
    """

    @staticmethod
    def calculer(produit_fini, quantite_a_produire):
        """
        Retourne une liste de dicts contenant les calculs MRP pour chaque composant.
        """
        resultats = []
        nomenclature_active = produit_fini.nomenclatures.filter(actif=True).first()
        
        if not nomenclature_active:
            return resultats
            
        lignes = nomenclature_active.lignes.select_related("matiere", "matiere__unite")
        
        q_prod = float(quantite_a_produire)

        for nom in lignes:
            m = nom.matiere
            
            # 1. Besoin Brut (BB)
            bb = q_prod * float(nom.quantite_par_unite)
            
            # 2. Besoin Ajusté (BA) avec taux de rebut (matière + nomenclature)
            taux_total = float(m.taux_rebut) + float(nom.taux_perte)
            ba = bb / (1 - taux_total) if taux_total < 1 else bb
            
            stock_dispo = float(m.stock_actuel)
            stock_ratio = (stock_dispo / ba * 100) if ba > 0 else 100
            
            if m.methode_approvisionnement != 'MRP':
                bn = max(0.0, ba - stock_dispo)
                qp = 0.0
                statut = "NON_MRP"
            else:
                # 3. Besoin Net (BN) = BA - Stock Actuel
                bn = max(0.0, ba - stock_dispo)
                
                # 4. Quantité Proposée (QP) avec lotissement
                qp = ExplosionBesoinsMRP.ajuster_par_lots(bn, m)
                
                # 5. Détermination du statut
                if stock_dispo >= ba:
                    statut = "SUFFISANT"
                elif stock_dispo > 0:
                    statut = "A_COMMANDER"
                elif bn > 0:
                    statut = "RUPTURE"
                else:
                    statut = "CRITIQUE"

            resultats.append({
                "matiere": m,
                "besoin_brut": round(bb, 4),
                "besoin_ajuste": round(ba, 4),
                "besoin_net": round(bn, 4),
                "quantite_proposee": round(qp, 4),
                "stock_actuel": stock_dispo,
                "stock_ratio": round(min(100.0, stock_ratio), 1),
                "statut": statut,
                "unite": m.unite.symbole if m.unite else "",
                "bloquant": stock_dispo < ba and nom.obligatoire,
            })
            
        return resultats

    @staticmethod
    def ajuster_par_lots(quantite, matiere):
        """Applique les règles de lot minimum et de multiple de lot."""
        if quantite <= 0:
            return 0.0
            
        res = quantite
        lot_min = float(matiere.lot_minimum)
        multiple = float(matiere.multiple_lot)
        
        # Appliquer lot minimum
        if lot_min > 0 and res < lot_min:
            res = lot_min
            
        # Appliquer multiple
        if multiple > 0:
            import math
            nb_lots = math.ceil(res / multiple)
            res = nb_lots * multiple
            
        return res
