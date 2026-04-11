"""
App Approvisionnement - Services (couche métier)
Calculs des 4 méthodes d'approvisionnement
"""

import math
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CalculReapproFixe:
    """
    Méthode 1 : RÉAPPROVISIONNEMENT À QUANTITÉ ET PÉRIODE FIXES
    Déclenche une commande de quantité Q fixe tous les T jours.
    """

    @classmethod
    def generer_suggestions(cls):
        """Générer les suggestions pour tous les produits en REAPPRO_FIXE."""
        from produits.models import Produit
        from .models import SuggestionAppro, ParametreAppro

        suggestions_creees = []
        produits = Produit.objects.filter(
            methode_appro='REAPPRO_FIXE', statut='ACTIF'
        ).select_related('parametre_appro', 'unite_stock', 'fournisseur_principal')

        today = timezone.now().date()

        for produit in produits:
            try:
                param = produit.parametre_appro
            except ParametreAppro.DoesNotExist:
                continue

            # Vérifier si c'est le jour de commande
            if not param.date_prochaine_commande or param.date_prochaine_commande <= today:
                sugg = SuggestionAppro.objects.create(
                    produit=produit,
                    fournisseur=produit.fournisseur_principal,
                    methode='REAPPRO_FIXE',
                    quantite_suggeree=param.quantite_commande_fixe or 0,
                    stock_au_moment=produit.stock_actuel,
                    justification=(
                        f"Méthode Réappro Fixe : Date de commande atteinte.\n"
                        f"Quantité fixe = {param.quantite_commande_fixe} {produit.unite_stock.code}\n"
                        f"Stock actuel = {produit.stock_actuel}\n"
                        f"Périodicité = tous les {param.periodicite_commande or '?'} jours"
                    ),
                    date_commande_prevue=today,
                    date_livraison_prevue=today + timezone.timedelta(days=produit.delai_reappro),
                )
                # Mettre à jour la prochaine date de commande
                if param.periodicite_commande:
                    param.date_prochaine_commande = today + timezone.timedelta(days=param.periodicite_commande)
                    param.save(update_fields=['date_prochaine_commande'])
                suggestions_creees.append(sugg)

        return suggestions_creees


class CalculPointCommande:
    """
    Méthode 2 : POINT DE COMMANDE (ROP — Reorder Point)
    Commander quand stock_actuel <= Point de commande.
    Quantité commandée = QEC (Wilson).
    """

    @classmethod
    def generer_suggestions(cls):
        """Générer les suggestions ROP pour tous les produits concernés."""
        from produits.models import Produit
        from .models import SuggestionAppro, ParametreAppro
        from django.db.models import F

        suggestions_creees = []
        today = timezone.now().date()

        produits_en_alerte = Produit.objects.filter(
            methode_appro='POINT_COMMANDE',
            statut='ACTIF',
            stock_actuel__lte=F('point_commande'),
        ).select_related('parametre_appro', 'unite_stock', 'fournisseur_principal')

        for produit in produits_en_alerte:
            # Vérifier qu'il n'existe pas déjà une suggestion active
            existe = SuggestionAppro.objects.filter(
                produit=produit,
                statut='NOUVELLE',
                methode='POINT_COMMANDE',
            ).exists()
            if existe:
                continue

            try:
                param = produit.parametre_appro
                qec = float(param.qec_calcule or produit.quantite_economique or 0)
                ss = float(param.stock_securite_calcule or produit.stock_securite or 0)
                rop = float(param.point_commande_calcule or produit.point_commande or 0)
            except Exception:
                qec = float(produit.quantite_economique or 0)
                ss = float(produit.stock_securite or 0)
                rop = float(produit.point_commande or 0)

            urgente = float(produit.stock_actuel) <= float(produit.stock_securite)

            sugg = SuggestionAppro.objects.create(
                produit=produit,
                fournisseur=produit.fournisseur_principal,
                methode='POINT_COMMANDE',
                quantite_suggeree=max(qec, 1),
                stock_au_moment=produit.stock_actuel,
                urgente=urgente,
                justification=(
                    f"Méthode Point de Commande (ROP) :\n"
                    f"Stock actuel = {produit.stock_actuel} {produit.unite_stock.code}\n"
                    f"Point de commande = {rop}\n"
                    f"Stock de sécurité = {ss}\n"
                    f"QEC (Wilson) = {qec:.2f}\n"
                    f"{'⚠️ URGENT : Stock sous le seuil de sécurité !' if urgente else ''}"
                ),
                date_commande_prevue=today,
                date_livraison_prevue=today + timezone.timedelta(days=produit.delai_reappro),
            )
            suggestions_creees.append(sugg)

        return suggestions_creees


class CalculRecompletement:
    """
    Méthode 3 : RÉCOMPLETEMENT PÉRIODIQUE (S, T)
    À chaque période T, commander : Q = S - stock_actuel
    S = Stock cible (niveau maximum à atteindre)
    """

    @classmethod
    def generer_suggestions(cls):
        """Générer les suggestions de récompletement."""
        from produits.models import Produit
        from .models import SuggestionAppro, ParametreAppro

        suggestions_creees = []
        today = timezone.now().date()

        produits = Produit.objects.filter(
            methode_appro='RECOMPLETEMENT',
            statut='ACTIF',
        ).select_related('parametre_appro', 'unite_stock', 'fournisseur_principal')

        for produit in produits:
            try:
                param = produit.parametre_appro
                stock_cible = float(param.stock_cible or produit.stock_maximum or 0)
                periode = param.periode_revision or 30
            except Exception:
                stock_cible = float(produit.stock_maximum or 0)
                periode = 30

            stock_actuel = float(produit.stock_actuel)
            quantite_a_commander = max(0, stock_cible - stock_actuel)

            if quantite_a_commander <= 0:
                continue

            sugg = SuggestionAppro.objects.create(
                produit=produit,
                fournisseur=produit.fournisseur_principal,
                methode='RECOMPLETEMENT',
                quantite_suggeree=quantite_a_commander,
                stock_au_moment=produit.stock_actuel,
                justification=(
                    f"Méthode Récompletement (S, T) :\n"
                    f"Stock actuel = {stock_actuel} {produit.unite_stock.code}\n"
                    f"Stock cible S = {stock_cible}\n"
                    f"Période de révision T = {periode} jours\n"
                    f"Quantité à commander = S - Stock actuel = {quantite_a_commander:.3f}"
                ),
                date_commande_prevue=today,
                date_livraison_prevue=today + timezone.timedelta(days=produit.delai_reappro),
            )
            suggestions_creees.append(sugg)

        return suggestions_creees


class CalculMRP:
    """
    Méthode 4 : MRP (Material Requirements Planning)
    Calcul des besoins en matières sur un horizon de planification.

    Algorithme :
    1. Pour chaque semaine de l'horizon :
       - Besoin brut (BB) = consommation prévisionnelle
       - Besoin net (BN) = max(0, BB - Stock disponible - RP)
       - Si BN > 0 : générer un ordre proposé en t - délai
    2. Tenir compte des réceptions programmées
    3. Propager les ordres lancés en avance
    """

    @classmethod
    def executer(cls, plan):
        """Exécuter le calcul MRP pour un plan donné."""
        from produits.models import Produit
        from .models import LigneMRP, ParametreAppro
        import datetime

        produits_mrp = Produit.objects.filter(
            methode_appro='MRP', statut='ACTIF'
        ).select_related('parametre_appro', 'unite_stock')

        nb_lignes = 0
        date_courante = plan.date_debut

        for produit in produits_mrp:
            try:
                param = produit.parametre_appro
                cjm = float(param.consommation_journaliere_moyenne)
                lot_multiple = float(param.lot_multiple or 1)
                coeff = float(param.nomenclature_coefficient)
            except Exception:
                cjm = 0
                lot_multiple = 1
                coeff = 1

            stock_disponible = float(produit.stock_actuel)
            semaine_debut = date_courante.isocalendar()[1]
            annee_debut = date_courante.year

            for semaine_offset in range(plan.horizon_semaines):
                # Calcul de la semaine courante
                date_semaine = date_courante + datetime.timedelta(weeks=semaine_offset)
                semaine = date_semaine.isocalendar()[1]
                annee = date_semaine.year

                # Besoin brut = CJM × 7 × coefficient
                besoin_brut = cjm * 7 * coeff

                # Besoin net
                besoin_net = max(0, besoin_brut - stock_disponible)

                # Arrondir au lot multiple supérieur
                if besoin_net > 0 and lot_multiple > 1:
                    ordre = math.ceil(besoin_net / lot_multiple) * lot_multiple
                else:
                    ordre = besoin_net

                # Mise à jour du stock disponible projeté
                stock_disponible = max(0, stock_disponible - besoin_brut + ordre)

                ligne, _ = LigneMRP.objects.update_or_create(
                    plan=plan,
                    produit=produit,
                    semaine=semaine,
                    annee=annee,
                    defaults={
                        'besoin_brut': round(besoin_brut, 3),
                        'besoin_net': round(besoin_net, 3),
                        'ordre_propose': round(ordre, 3),
                        'stock_disponible': round(stock_disponible, 3),
                    }
                )
                nb_lignes += 1

        return nb_lignes
