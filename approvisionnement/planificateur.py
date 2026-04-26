"""
approvisionnement/planificateur.py
Moteur de calcul des propositions de commande par méthode.
Chaque méthode a sa propre fonction qui retourne un dict avec
quantite_proposee, detail_calcul, urgence, date_besoin — ou None si pas besoin.
"""

from datetime import date, timedelta
from produits.models import MatierePremiere
from .models import PropositionCommande


# ============================================================
# CALCULATEURS PAR MÉTHODE
# ============================================================

def calculer_point_commande(matiere):
    """
    Méthode ROP : commande de QEC quand stock <= point_commande.
    Urgente si stock <= stock_securite ou stock <= 0.
    """
    stock  = float(matiere.stock_actuel)
    rop    = float(matiere.point_commande)
    qec    = float(matiere.qec)
    s_secu = float(matiere.stock_securite)
    delai  = matiere.delai_livraison_jours

    if stock > rop:
        return None  # Pas besoin de commander

    quantite    = qec if qec > 0 else max(0.0, float(matiere.stock_maximum) - stock)
    urgente     = stock <= s_secu or stock <= 0
    date_besoin = date.today() + timedelta(days=delai)

    return {
        "quantite_proposee": round(quantite, 4),
        "urgence":     urgente,
        "date_besoin": date_besoin,
        "detail_calcul": {
            "methode":        "POINT_COMMANDE",
            "stock_actuel":   stock,
            "point_commande": rop,
            "qec":            qec,
            "stock_securite": s_secu,
            "delai_jours":    delai,
            "regle":          f"Stock ({stock}) ≤ ROP ({rop}) → commander QEC = {quantite}",
        },
    }


def calculer_reappro_fixe(matiere):
    """
    Méthode Q fixe (Q, T) : commande de QEC à chaque période T.
    Déclenche si aucune commande confirme/reçue dans la période T.
    """
    from .models import BonCommande
    from django.utils import timezone as tz

    stock   = float(matiere.stock_actuel)
    qec     = float(matiere.qec)
    periode = matiere.periode_reappro_jours
    delai   = matiere.delai_livraison_jours
    s_min   = float(matiere.stock_minimum)

    depuis = tz.now() - timedelta(days=periode)
    commande_recente = BonCommande.objects.filter(
        matiere=matiere,
        date_creation__gte=depuis,
        statut__in=["ENVOYE", "CONFIRME", "RECU"]
    ).exists()

    if commande_recente and stock > s_min:
        return None  # Déjà commandé dans la période

    quantite    = qec if qec > 0 else max(0.0, float(matiere.stock_maximum) - stock)
    urgente     = stock <= 0 or stock <= float(matiere.stock_securite)
    date_besoin = date.today() + timedelta(days=delai)

    return {
        "quantite_proposee": round(quantite, 4),
        "urgence":     urgente,
        "date_besoin": date_besoin,
        "detail_calcul": {
            "methode":          "REAPPRO_FIXE",
            "stock_actuel":     stock,
            "qec":              quantite,
            "periode_jours":    periode,
            "delai_jours":      delai,
            "commande_recente": commande_recente,
            "regle":            f"Période T={periode}j écoulée → commander Q fixe = {quantite}",
        },
    }


def calculer_recompletement(matiere):
    """
    Méthode Recomplètement (S, T) : commande S − stock actuel.
    S = stock_maximum = niveau cible.
    """
    stock   = float(matiere.stock_actuel)
    s_max   = float(matiere.stock_maximum)
    periode = matiere.periode_reappro_jours
    delai   = matiere.delai_livraison_jours
    s_secu  = float(matiere.stock_securite)

    quantite = max(0.0, s_max - stock)
    if quantite <= 0:
        return None  # Stock au niveau cible

    urgente     = stock <= 0 or stock <= s_secu
    date_besoin = date.today() + timedelta(days=delai)

    return {
        "quantite_proposee": round(quantite, 4),
        "urgence":     urgente,
        "date_besoin": date_besoin,
        "detail_calcul": {
            "methode":       "RECOMPLETEMENT",
            "stock_actuel":  stock,
            "niveau_cible":  s_max,
            "periode_jours": periode,
            "delai_jours":   delai,
            "regle":         f"S − stock = {s_max} − {stock} = {quantite}",
        },
    }


def calculer_mrp(matiere):
    """
    Méthode MRP : lit le plan MRP actif (statut=CALCULE, besoin_net > 0).
    """
    from .models import PlanMRP

    plan = PlanMRP.objects.filter(
        matiere=matiere,
        statut=PlanMRP.Statut.CALCULE,
        besoin_net__gt=0,
    ).order_by("periode").first()

    if not plan:
        return None

    quantite = float(plan.quantite_proposee)
    if quantite <= 0:
        return None

    return {
        "quantite_proposee": round(quantite, 4),
        "urgence":     float(matiere.stock_actuel) <= 0,
        "date_besoin": plan.periode,
        "detail_calcul": {
            "methode":      "MRP",
            "plan_periode": str(plan.periode),
            "besoin_brut":  float(plan.besoin_brut),
            "besoin_net":   float(plan.besoin_net),
            "stock_debut":  float(plan.stock_debut_periode),
            "taux_rebut":   float(matiere.taux_rebut),
            "regle":        f"Plan MRP période {plan.periode} : besoin net = {plan.besoin_net}",
        },
    }


# ── Dispatch table ──────────────────────────────────────────
CALCULATEURS = {
    "POINT_COMMANDE": calculer_point_commande,
    "REAPPRO_FIXE":   calculer_reappro_fixe,
    "RECOMPLETEMENT": calculer_recompletement,
    "MRP":            calculer_mrp,
}


# ============================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================

def lancer_planification(matieres=None, force=False):
    """
    Parcourt toutes les matières actives (ou le subset fourni),
    applique le calculateur selon la méthode, crée les PropositionCommande.

    Args:
        matieres: queryset optionnel (toutes les matières actives si None)
        force:    si True, recalcule même si une proposition PROPOSÉE existe déjà

    Returns:
        dict { "creees": int, "ignorees": int, "erreurs": list[str] }
    """
    if matieres is None:
        matieres = MatierePremiere.objects.filter(actif=True).select_related(
            "unite", "fournisseur_principal"
        )

    resultats = {"creees": 0, "ignorees": 0, "erreurs": []}

    for matiere in matieres:
        methode     = matiere.methode_approvisionnement
        calculateur = CALCULATEURS.get(methode)
        if not calculateur:
            resultats["ignorees"] += 1
            continue

        # Éviter les doublons
        if not force and PropositionCommande.objects.filter(
            matiere=matiere,
            statut=PropositionCommande.Statut.EN_ATTENTE
        ).exists():
            resultats["ignorees"] += 1
            continue

        try:
            result = calculateur(matiere)
            if result is None:
                resultats["ignorees"] += 1
                continue

            PropositionCommande.objects.create(
                matiere           = matiere,
                methode           = methode,
                quantite_proposee = result["quantite_proposee"],
                urgence           = result["urgence"],
                date_besoin       = result.get("date_besoin"),
                detail_calcul     = result["detail_calcul"],
                statut            = PropositionCommande.Statut.EN_ATTENTE,
            )
            resultats["creees"] += 1

        except Exception as exc:
            resultats["erreurs"].append(f"{matiere.reference}: {exc}")

    return resultats
