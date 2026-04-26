"""
produits/abc_recommandation.py
MediCare Industries — Moteur de recommandation ABC × Méthode d'approvisionnement.

Fonction principale : recommander_methode_approvisionnement(matiere)
Retourne un dictionnaire structuré avec :
  - methode_recommandee
  - justification
  - methode_alternative
  - niveau_confiance  ('faible', 'moyen', 'eleve')
  - historique_suffisant  (bool)
  - classe_abc  ('A', 'B', 'C' ou None)
  - nb_mouvements_sorties
  - seuil_historique_utilise
"""

from __future__ import annotations

# ── Seuils d'historique ──────────────────────────────────────────────────────
# Nombre minimum de mouvements de sortie sur 12 mois pour estimer la classe ABC
SEUIL_HISTORIQUE_FAIBLE  = 3    # < 3  sorties → confiance faible
SEUIL_HISTORIQUE_MOYEN   = 12   # < 12 sorties → confiance moyenne
# >= 12 sorties → confiance élevée


# ── Règles de recommandation ─────────────────────────────────────────────────

_REGLES = {
    "A": {
        "methode":      "POINT_COMMANDE",
        "alternative":  "MRP",
        "justification": (
            "Les articles de classe A ont une forte valeur de consommation. "
            "Le suivi en continu (Point de commande / ROP) permet de réagir "
            "immédiatement à chaque sortie et d'éviter toute rupture critique. "
            "Si cette matière est liée à un produit fini, envisagez le MRP."
        ),
    },
    "B": {
        "methode":      "REAPPRO_FIXE",
        "alternative":  "POINT_COMMANDE",
        "justification": (
            "Les articles de classe B ont une valeur intermédiaire. "
            "Un réapprovisionnement à quantité fixe (Q, T) offre un bon compromis "
            "entre simplicité de gestion et maîtrise des coûts. "
            "Le Point de commande reste une alternative viable si la consommation est irrégulière."
        ),
    },
    "C": {
        "methode":      "RECOMPLETEMENT",
        "alternative":  "REAPPRO_FIXE",
        "justification": (
            "Les articles de classe C ont une faible valeur de consommation. "
            "La méthode de recomplètement (révision périodique) minimise les coûts "
            "de gestion tout en maintenant un niveau de stock suffisant. "
            "Le réapprovisionnement fixe est une alternative simple."
        ),
    },
}

_REGLES_SANS_HISTORIQUE = {
    "methode":      "POINT_COMMANDE",
    "alternative":  "REAPPRO_FIXE",
    "justification": (
        "Aucun historique de consommation suffisant n'est disponible. "
        "Le Point de commande est recommandé par défaut pour les nouvelles matières, "
        "car il offre une surveillance continue du stock. "
        "Vous pourrez réévaluer la méthode après quelques semaines d'activité."
    ),
}

# Message affiché en interface quand l'historique est insuffisant
MESSAGE_HISTORIQUE_INSUFFISANT = (
    "La recommandation automatique de méthode d'approvisionnement nécessite un historique "
    "suffisant de consommation ou de mouvements. Vous pouvez choisir une méthode manuellement "
    "pour le démarrage, puis réévaluer après quelques semaines d'activité."
)


# ── Fonctions publiques ──────────────────────────────────────────────────────

def _niveau_confiance(nb_sorties: int) -> str:
    """Retourne le niveau de confiance de la recommandation."""
    if nb_sorties < SEUIL_HISTORIQUE_FAIBLE:
        return "faible"
    if nb_sorties < SEUIL_HISTORIQUE_MOYEN:
        return "moyen"
    return "eleve"


def _calculer_classe_abc_dynamique(matiere) -> str | None:
    """
    Calcule la classe ABC d'une matière sans toucher à la base de données.
    Basé uniquement sur la valeur de consommation annuelle de CETTE matière.
    (Classement absolu simplifié — pas de tri global par rapport à l'ensemble.)

    Pour un classement ABC rigoureux (Pareto sur toutes les matières),
    utiliser la management command `calculer_abc`.
    """
    # Si la classe ABC est déjà persistée en BDD, la retourner directement
    if matiere.classe_abc:
        return matiere.classe_abc

    # Estimation dynamique locale (utilisée uniquement si classe_abc non persistée)
    valeur = matiere.valeur_consommation_annuelle
    prix   = float(matiere.prix_unitaire)

    if valeur <= 0 and prix <= 0:
        return None  # Impossible à classer

    # Heuristique locale : basée sur la valeur absolue de consommation
    # Seuils représentatifs d'un contexte pharmaceutique (ajustables)
    if valeur >= 50_000:
        return "A"
    if valeur >= 10_000:
        return "B"
    if valeur > 0:
        return "C"
    return None


def recommander_methode_approvisionnement(matiere) -> dict:
    """
    Analyse la matière première et recommande une méthode d'approvisionnement.

    Paramètres
    ----------
    matiere : MatierePremiere
        Instance du modèle matière (doit être déjà sauvegardée pour avoir
        des mouvements).

    Retourne
    --------
    dict avec les clés :
        methode_recommandee   : str  ('POINT_COMMANDE', 'REAPPRO_FIXE', etc.)
        methode_alternative   : str  (méthode de seconde recommandation)
        justification         : str
        niveau_confiance      : str  ('faible', 'moyen', 'eleve')
        historique_suffisant  : bool
        classe_abc            : str | None ('A', 'B', 'C' ou None)
        nb_mouvements_sorties : int
        seuil_historique_utilise : dict
        message_historique_insuffisant : str | None
    """
    # 1. Compter l'historique de sorties
    nb_sorties = matiere.nb_sorties_12_mois if matiere.pk else 0

    # 2. Déterminer si l'historique est suffisant
    historique_suffisant = (nb_sorties >= SEUIL_HISTORIQUE_FAIBLE)

    # 3. Niveau de confiance
    niveau_confiance = _niveau_confiance(nb_sorties)

    # 4. Classe ABC
    classe_abc = _calculer_classe_abc_dynamique(matiere)

    # 5. Règle de recommandation
    if not historique_suffisant or classe_abc is None:
        regle = _REGLES_SANS_HISTORIQUE
        message_insuff = MESSAGE_HISTORIQUE_INSUFFISANT
    else:
        regle = _REGLES.get(classe_abc, _REGLES_SANS_HISTORIQUE)
        message_insuff = None

    return {
        "methode_recommandee":          regle["methode"],
        "methode_alternative":          regle["alternative"],
        "justification":                regle["justification"],
        "niveau_confiance":             niveau_confiance,
        "historique_suffisant":         historique_suffisant,
        "classe_abc":                   classe_abc,
        "nb_mouvements_sorties":        nb_sorties,
        "seuil_historique_utilise": {
            "faible": SEUIL_HISTORIQUE_FAIBLE,
            "moyen":  SEUIL_HISTORIQUE_MOYEN,
        },
        "message_historique_insuffisant": message_insuff,
    }


def calculer_abc_global() -> list[dict]:
    """
    Calcule la classification ABC de TOUTES les matières (analyse de Pareto).
    Met à jour le champ `classe_abc` en base de données.

    Algorithme :
      1. Calculer la valeur de consommation annuelle par matière (sorties × prix)
      2. Trier par valeur décroissante
      3. Calculer le % cumulé
      4. A = 0–80 %, B = 80–95 %, C = 95–100 %

    Retourne la liste des résultats pour log/affichage.
    """
    from .models import MatierePremiere

    matieres = list(MatierePremiere.objects.prefetch_related("mouvements").all())

    # Calculer valeur consommation
    valeurs = []
    for m in matieres:
        v = m.valeur_consommation_annuelle
        valeurs.append({"matiere": m, "valeur": v})

    # Trier par valeur décroissante
    valeurs.sort(key=lambda x: x["valeur"], reverse=True)

    total = sum(v["valeur"] for v in valeurs)
    cumul = 0.0
    resultats = []

    for item in valeurs:
        m = item["matiere"]
        v = item["valeur"]

        if total > 0:
            cumul += v
            pct_cumul = (cumul / total) * 100
        else:
            pct_cumul = 100.0  # Aucune consommation → tout en C

        if pct_cumul <= 80:
            classe = "A"
        elif pct_cumul <= 95:
            classe = "B"
        else:
            classe = "C"

        # Persister en BDD
        m.classe_abc = classe
        m.save(update_fields=["classe_abc"])

        resultats.append({
            "reference": m.reference,
            "nom":       m.nom,
            "valeur":    round(v, 2),
            "pct_cumul": round(pct_cumul, 2),
            "classe":    classe,
        })

    return resultats
