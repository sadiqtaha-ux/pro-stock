# Guide de contribution — StockPro 🏥

> Projet Django 4.2 — MediCare Industries, Meknès  
> Ce guide explique comment chaque membre de l'équipe doit travailler sur le projet.

---

## 📋 Organisation des branches

| Branche | Rôle | Responsable |
|---|---|---|
| `main` | Production — code validé et déployé | Chef de projet |
| `develop` | Intégration — fusion de toutes les features | Chef de projet |
| `feature/p1-setup` | Auth, modèles de base, déploiement | Membre 1 (Chef projet) |
| `feature/p2-mouvements` | Entrées/sorties, mouvements de stock | Membre 2 (Backend stocks) |
| `feature/p3-approvisionnement` | 4 méthodes d'approvisionnement | Membre 3 (Backend appro) |
| `feature/p4-frontend` | Templates HTML, Dashboard, CSS/JS | Membre 4 (Frontend) |

---

## 🚀 Étape 1 — Cloner le projet

```bash
git clone <URL_DU_DEPOT>
cd stockpro
```

---

## 🐍 Étape 2 — Configurer l'environnement local

```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# Installer les dépendances
pip install -r requirements.txt

# Copier et configurer les variables d'environnement
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
# Éditer le fichier .env avec vos valeurs

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

---

## 🌿 Étape 3 — Travailler sur votre branche

Chaque membre travaille **uniquement** sur sa branche assignée.

```bash
# Basculer sur votre branche
git checkout feature/p2-mouvements   # ← Remplacer par votre branche

# Avant tout travail, récupérer les dernières mises à jour de develop
git fetch origin
git rebase origin/develop
```

---

## 💾 Étape 4 — Commiter votre travail

Utilisez des messages de commit clairs et en français.

```bash
# Voir les fichiers modifiés
git status

# Ajouter les fichiers à commiter
git add nom_du_fichier.py          # Fichier spécifique
# OU
git add .                           # Tous les fichiers modifiés

# Créer le commit avec un message descriptif
git commit -m "feat: ajout du formulaire de bon d'entrée"

# Envoyer vers GitHub/GitLab
git push origin feature/p2-mouvements   # ← Votre branche
```

### 📝 Convention des messages de commit

| Préfixe | Usage |
|---|---|
| `feat:` | Nouvelle fonctionnalité |
| `fix:` | Correction de bug |
| `docs:` | Documentation |
| `style:` | Mise en forme, CSS |
| `refactor:` | Refactorisation du code |
| `test:` | Ajout de tests |
| `chore:` | Tâches de maintenance |

**Exemples :**
```
feat: implémentation de la méthode de calcul ROP
fix: correction du calcul du stock de sécurité
docs: mise à jour du README avec les instructions d'installation
style: amélioration du design de la page produits
```

---

## 🔄 Étape 5 — Créer une Pull Request (PR)

Une fois votre fonctionnalité terminée et testée :

1. Poussez votre branche sur le dépôt distant :
   ```bash
   git push origin feature/votre-branche
   ```

2. Allez sur GitHub/GitLab et cliquez sur **"New Pull Request"** (ou "Merge Request").

3. Configurez la PR :
   - **Source :** votre branche (ex: `feature/p2-mouvements`)
   - **Destination :** `develop` (**jamais directement vers `main`**)
   - **Titre :** Décrivez clairement ce que vous avez fait
   - **Description :** Listez les changements effectués

4. Assignez la PR au **Chef de projet** pour revue.

5. Attendez la validation avant de merger.

---

## ⚠️ Règles importantes

- **Ne jamais pousser directement sur `main` ou `develop`**
- **Ne jamais commiter le fichier `.env`** (il contient des mots de passe)
- Toujours **tester localement** avant de créer une PR
- Garder les commits **petits et cohérents** (une fonctionnalité = un commit)
- En cas de conflit Git, contactez le **Chef de projet**

---

## 🆘 Résolution des conflits Git

Si vous avez un conflit lors d'un `rebase` ou `merge` :

```bash
# Voir les fichiers en conflit
git status

# Après avoir résolu les conflits manuellement dans votre éditeur
git add fichier_en_conflit.py
git rebase --continue    # Si vous étiez en rebase
# ou
git commit               # Si vous étiez en merge
```

---

## 📞 Contact

En cas de problème technique, contacter le Chef de projet.

---

*StockPro — MediCare Industries © 2026*
