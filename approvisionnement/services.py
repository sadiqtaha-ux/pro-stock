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


class CalculReapproFixe:
    """
    Méthode REAPPRO_FIXE : commande de quantité Q fixe à période T fixe.
    On commande toujours la QEC (quantité économique).
    """

    @staticmethod
    def generer_bons(utilisateur=None):
        """
        Parcourt toutes les matières en REAPPRO_FIXE dont la date
        de réapprovisionnement est atteinte, et génère un BonCommande.
        Retourne la liste des bons créés.
        """
        bons = []
        aujourd_hui = timezone.now().date()
        matieres = MatierePremiere.objects.filter(
            methode_approvisionnement=MatierePremiere.MethodeApprovisionnement.REAPPRO_FIXE,
            actif=True,
            fournisseur_principal__isnull=False,
        )
        for m in matieres:
            # Commande si stock inférieur au point de commande
            if m.stock_actuel <= m.point_commande:
                qte = m.qec if m.qec > 0 else m.stock_maximum - m.stock_actuel
                bon = BonCommande.objects.create(
                    matiere=m,
                    fournisseur=m.fournisseur_principal,
                    quantite_commandee=qte,
                    prix_unitaire=m.prix_unitaire,
                    methode_declenchement=BonCommande.MethodeDeclenchement.REAPPRO_FIXE,
                    statut=BonCommande.Statut.BROUILLON,
                    cree_par=utilisateur,
                )
                bons.append(bon)
        return bons


class CalculPointCommande:
    """
    Méthode POINT_COMMANDE (ROP) :
    Déclenche une commande quand stock <= ROP.
    ROP = Consommation Journalière Moyenne × Délai + Stock Sécurité
    QEC = √(2 × D × K / (h × Pu))  [Wilson]
    """

    @staticmethod
    def calculer_qec(
        demande_annuelle: float,
        cout_passation: float,
        cout_possession_pct: float,
        prix_unitaire: float,
    ) -> float:
        """Formule de Wilson."""
        h = cout_possession_pct * prix_unitaire
        if h <= 0 or prix_unitaire <= 0:
            return 0.0
        return math.sqrt(2 * demande_annuelle * cout_passation / h)

    @staticmethod
    def generer_bons(utilisateur=None):
        bons = []
        matieres = MatierePremiere.objects.filter(
            methode_approvisionnement=MatierePremiere.MethodeApprovisionnement.POINT_COMMANDE,
            actif=True,
            fournisseur_principal__isnull=False,
        )
        for m in matieres:
            if m.stock_actuel <= m.point_commande:
                qte = m.qec if m.qec > 0 else (m.stock_maximum - m.stock_actuel)
                bon = BonCommande.objects.create(
                    matiere=m,
                    fournisseur=m.fournisseur_principal,
                    quantite_commandee=qte,
                    prix_unitaire=m.prix_unitaire,
                    methode_declenchement=BonCommande.MethodeDeclenchement.POINT_COMMANDE,
                    statut=BonCommande.Statut.BROUILLON,
                    cree_par=utilisateur,
                )
                bons.append(bon)
        return bons


class CalculRecompletement:
    """
    Méthode RECOMPLETEMENT (S, T) — Révision périodique.
    À chaque période T, on commande : S - stock_actuel
    Stock cible S = CJM × (T + L) + SS
    """

    @staticmethod
    def calculer_stock_cible(
        consommation_journaliere: float,
        periode_jours: int,
        delai_livraison_jours: int,
        stock_securite: float,
    ) -> float:
        return consommation_journaliere * (periode_jours + delai_livraison_jours) + stock_securite

    @staticmethod
    def generer_bons(utilisateur=None):
        bons = []
        matieres = MatierePremiere.objects.filter(
            methode_approvisionnement=MatierePremiere.MethodeApprovisionnement.RECOMPLETEMENT,
            actif=True,
            fournisseur_principal__isnull=False,
        )
        for m in matieres:
            qte = m.stock_maximum - m.stock_actuel
            if qte > 0:
                bon = BonCommande.objects.create(
                    matiere=m,
                    fournisseur=m.fournisseur_principal,
                    quantite_commandee=qte,
                    prix_unitaire=m.prix_unitaire,
                    methode_declenchement=BonCommande.MethodeDeclenchement.RECOMPLETEMENT,
                    statut=BonCommande.Statut.BROUILLON,
                    cree_par=utilisateur,
                )
                bons.append(bon)
        return bons


class CalculMRP:
    """
    Méthode MRP (Material Requirements Planning).
    Calcul : BN = max(0, BB - Stock_début - Réceptions)
    QP = BN / (1 - taux_rebut)
    """

    @staticmethod
    def calculer_besoin_net(
        besoin_brut: float,
        stock_debut: float,
        receptions_prevues: float = 0,
    ) -> float:
        return max(0.0, besoin_brut - stock_debut - receptions_prevues)

    @staticmethod
    def calculer_quantite_proposee(besoin_net: float, taux_rebut: float = 0) -> float:
        if taux_rebut >= 1:
            return besoin_net
        return besoin_net / (1 - taux_rebut) if besoin_net > 0 else 0

    @staticmethod
    def executer_plan(matieres=None, utilisateur=None):
        """
        Crée les lignes BonCommande pour toutes les matières en méthode MRP
        dont le besoin net est positif.
        """
        from .models import PlanMRP
        bons = []
        if matieres is None:
            matieres = MatierePremiere.objects.filter(
                methode_approvisionnement=MatierePremiere.MethodeApprovisionnement.MRP,
                actif=True,
                fournisseur_principal__isnull=False,
            )
        for m in matieres:
            bn = CalculMRP.calculer_besoin_net(
                besoin_brut=float(m.stock_minimum),
                stock_debut=float(m.stock_actuel),
            )
            qp = CalculMRP.calculer_quantite_proposee(bn, float(m.taux_rebut))
            if qp > 0:
                bon = BonCommande.objects.create(
                    matiere=m,
                    fournisseur=m.fournisseur_principal,
                    quantite_commandee=Decimal(str(round(qp, 4))),
                    prix_unitaire=m.prix_unitaire,
                    methode_declenchement=BonCommande.MethodeDeclenchement.MRP,
                    statut=BonCommande.Statut.BROUILLON,
                    cree_par=utilisateur,
                )
                bons.append(bon)
        return bons
