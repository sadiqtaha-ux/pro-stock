"""
produits/management/commands/calculer_abc.py
MediCare Industries — Commande de calcul ABC global.

Usage :
    python manage.py calculer_abc
    python manage.py calculer_abc --dry-run
"""
from django.core.management.base import BaseCommand
from produits.abc_recommandation import calculer_abc_global


class Command(BaseCommand):
    help = (
        "Calcule la classification ABC de toutes les matières premières "
        "en fonction de leur valeur de consommation sur les 12 derniers mois. "
        "Met à jour le champ `classe_abc` en base de données."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les résultats sans modifier la base de données.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Mode dry-run : aucune modification en base.\n"))

        self.stdout.write("Calcul de la classification ABC en cours…\n")

        if not dry_run:
            resultats = calculer_abc_global()
        else:
            # Dry-run : importer le modèle et calculer sans sauvegarder
            from produits.models import MatierePremiere
            from django.utils import timezone
            from django.db.models import Sum
            import datetime

            matieres = list(MatierePremiere.objects.prefetch_related("mouvements").all())
            valeurs = []
            for m in matieres:
                v = m.valeur_consommation_annuelle
                valeurs.append({"matiere": m, "valeur": v})
            valeurs.sort(key=lambda x: x["valeur"], reverse=True)
            total = sum(v["valeur"] for v in valeurs)
            cumul = 0.0
            resultats = []
            for item in valeurs:
                m = item["matiere"]
                v = item["valeur"]
                cumul += v
                pct_cumul = (cumul / total * 100) if total > 0 else 100.0
                if pct_cumul <= 80:
                    classe = "A"
                elif pct_cumul <= 95:
                    classe = "B"
                else:
                    classe = "C"
                resultats.append({
                    "reference": m.reference,
                    "nom":       m.nom,
                    "valeur":    round(v, 2),
                    "pct_cumul": round(pct_cumul, 2),
                    "classe":    classe,
                })

        # Afficher le tableau
        self.stdout.write(
            f"\n{'Référence':<15} {'Nom':<35} {'Valeur conso (DH)':<20} {'% cumulé':<12} {'Classe'}"
        )
        self.stdout.write("-" * 90)

        compteurs = {"A": 0, "B": 0, "C": 0}
        for r in resultats:
            style = (
                self.style.ERROR   if r["classe"] == "A" else
                self.style.WARNING if r["classe"] == "B" else
                self.style.SUCCESS
            )
            self.stdout.write(style(
                f"{r['reference']:<15} {r['nom'][:35]:<35} {r['valeur']:<20,.2f} "
                f"{r['pct_cumul']:<12.2f} {r['classe']}"
            ))
            compteurs[r["classe"]] += 1

        self.stdout.write(f"\n{len(resultats)} matières traitées — "
                          f"A: {compteurs['A']} | B: {compteurs['B']} | C: {compteurs['C']}\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run terminé. Aucune modification appliquée."))
        else:
            self.stdout.write(self.style.SUCCESS("Classification ABC mise à jour en base de données."))
