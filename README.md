# StockPro — Gestion de Stock Pharmaceutique
### MediCare Industries — Meknès, Maroc 🇲🇦

> Système de gestion de stock pharmaceutique complet développé avec Django 4.2. Conçu pour les besoins spécifiques de **MediCare Industries** basée à Meknès.

---

## 🏗️ Architecture du projet

```
stockpro/
├── manage.py
├── requirements.txt
├── .env.example                  ← Variables d'environnement (à copier en .env)
├── README.md
│
├── stockpro/                     ← Package principal Django
│   ├── settings.py               ← Configuration complète (PostgreSQL, Celery, Redis...)
│   ├── urls.py                   ← URLs principales
│   ├── celery.py                 ← Configuration Celery
│   ├── wsgi.py / asgi.py
│   └── __init__.py
│
├── core/                         ← Authentification, base, middlewares
│   ├── models.py                 ← Utilisateur, JournalActivite, Notification, Parametre
│   ├── views.py                  ← Connexion, Profil, Utilisateurs, Notifications
│   ├── middleware.py             ← ActivityLog, StockAlert
│   ├── context_processors.py    ← company_info, nb_alertes, nav_perms
│   └── signals.py
│
├── produits/                     ← Matières premières, Fournisseurs, Catégories
│   ├── models.py                 ← Produit, Fournisseur, Lot, Tarif, Categorie, Unité
│   ├── views.py                  ← CRUD produits + API search JSON
│   └── ...
│
├── mouvements/                   ← Entrées, Sorties, Inventaires
│   ├── models.py                 ← MouvementStock, BonEntree, BonSortie, Inventaire
│   └── ...
│
├── approvisionnement/            ← 4 méthodes + Commandes d'achat + MRP
│   ├── models.py                 ← CommandeAchat, SuggestionAppro, PlanMRP, ParametreAppro
│   ├── services.py               ← CalculReapproFixe, CalculROP, CalculRecompletement, CalculMRP
│   └── ...
│
├── dashboard/                    ← KPIs, Graphiques, Rapports PDF
│   ├── models.py                 ← KPISnapshot, RapportSauvegarde
│   ├── views.py                  ← Dashboard + APIs Chart.js + ReportLab PDF
│   └── ...
│
├── magasin/                      ← Plan 2D, Zones, Rayons, Emplacements
│   ├── models.py                 ← ZoneStockage, Rayon, Emplacement, PlanMagasin
│   ├── views.py                  ← Vue 2D + API JSON plan
│   └── ...
│
├── templates/
│   └── base.html                 ← Template de base avec sidebar + topbar
├── static/
│   ├── css/stockpro.css          ← Styles CSS complets
│   └── js/stockpro.js            ← JavaScript (sidebar, Chart.js, KPI AJAX)
└── media/
```

---

## ⚙️ Méthodes d'approvisionnement

StockPro implémente les **4 méthodes** d'approvisionnement :

| Méthode | Description | Paramètres clés |
|---------|-------------|-----------------|
| **REAPPRO_FIXE** | Commande de quantité Q fixe à intervalles T fixes | Q, T (période), Date prochaine commande |
| **POINT_COMMANDE (ROP)** | Commander quand stock ≤ Point de commande | ROP = CJM × L + SS, QEC Wilson |
| **RECOMPLETEMENT (S,T)** | Révision périodique → atteindre stock cible S | S = CJM × (T+L) + SS |
| **MRP** | Calcul des besoins basé sur le programme de production | Nomenclature, lots, horizon |

**Formules implémentées :**
- `QEC (Wilson) = √(2 × D × K / (h × Pu))`
- `Stock Sécurité = z × σ × √(L)`
- `Point de Commande = CJM × L + SS`
- `Stock Cible S = CJM × (T + L) + SS`
- MRP : `BN = max(0, BB - RP - Stock dispo)`

---

## 🚀 Installation

### Prérequis

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Git

### 1. Cloner le projet

```bash
git clone <url-repo>
cd stockpro
```

### 2. Créer et activer l'environnement virtuel

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

Éditer le fichier `.env` :

```env
SECRET_KEY=votre-cle-secrete-generee-ici
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=stockpro_db
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
```

> **Générer une SECRET_KEY Django :**
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

### 5. Créer la base de données PostgreSQL

```sql
-- Dans psql ou pgAdmin :
CREATE DATABASE stockpro_db;
CREATE USER stockpro_user WITH PASSWORD 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE stockpro_db TO stockpro_user;
```

### 6. Appliquer les migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Créer le superutilisateur

```bash
python manage.py createsuperuser
```

### 8. Créer le dossier des logs

```bash
mkdir logs
```

### 9. Collecter les fichiers statiques (production)

```bash
python manage.py collectstatic --no-input
```

### 10. Lancer le serveur de développement

```bash
python manage.py runserver
```

📍 Accéder à l'application : **http://127.0.0.1:8000/**
📍 Administration Django : **http://127.0.0.1:8000/admin/**

---

## 🔄 Lancer Celery (tâches asynchrones)

```bash
# Worker Celery
celery -A stockpro worker --loglevel=info

# Scheduler Celery Beat (tâches périodiques)
celery -A stockpro beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## 📧 Configuration Email

Dans `.env` :
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe-app
```

---

## 🔐 Rôles utilisateurs

| Rôle | Permissions |
|------|-------------|
| **ADMIN** | Accès total, gestion des utilisateurs, paramètres |
| **RESPONSABLE_STOCK** | Validation des mouvements, commandes, rapports |
| **MAGASINIER** | Saisie entrées/sorties, consultation |
| **ACHETEUR** | Gestion des commandes fournisseurs, approvisionnement |
| **CONSULTANT** | Lecture seule — tous les modules |

---

## 📊 Technologies utilisées

| Composant | Technologie |
|-----------|-------------|
| Framework | Django 4.2 |
| Base de données | PostgreSQL + psycopg2 |
| Cache & Queue | Redis |
| Tâches asynchrones | Celery + django-celery-beat |
| UI | Bootstrap 5.3 + Bootstrap Icons |
| Graphiques | Chart.js 4.4 |
| Génération PDF | ReportLab |
| Formulaires | django-crispy-forms + crispy-bootstrap5 |
| Import/Export | django-import-export + openpyxl |
| Fichiers statiques prod. | WhiteNoise |
| Polices | Google Fonts (Inter) |

---

## 📁 URLs principales

| URL | Description |
|-----|-------------|
| `/` | Page de connexion |
| `/dashboard/` | Tableau de bord principal |
| `/produits/` | Liste des produits |
| `/produits/fournisseurs/` | Gestion des fournisseurs |
| `/mouvements/entrees/` | Bons d'entrée |
| `/mouvements/sorties/` | Bons de sortie |
| `/mouvements/inventaires/` | Inventaires |
| `/approvisionnement/` | Dashboard approvisionnement |
| `/approvisionnement/methodes/reappro-fixe/` | Méthode Réappro Fixe |
| `/approvisionnement/methodes/point-commande/` | Méthode ROP |
| `/approvisionnement/methodes/recompletement/` | Méthode S,T |
| `/approvisionnement/mrp/` | Plans MRP |
| `/magasin/` | Plan 2D du magasin |
| `/dashboard/rapports/` | Rapports & exports |
| `/admin/` | Administration Django |

---

## 🛠️ Commandes utiles

```bash
# Créer les données de test
python manage.py shell

# Vérifier la configuration
python manage.py check

# Générer les migrations après modification des modèles
python manage.py makemigrations

# Afficher le SQL d'une migration sans l'appliquer
python manage.py sqlmigrate produits 0001

# Vider le cache Redis
python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

---

## 🌐 Déploiement en production

Pour la production, assurez-vous de :

1. Mettre `DEBUG=False` dans `.env`
2. Configurer `ALLOWED_HOSTS` avec votre domaine
3. Utiliser `SECURE_SSL_REDIRECT=True` (HTTPS)
4. Exécuter `python manage.py collectstatic`
5. Utiliser Gunicorn + Nginx
6. Configurer Celery comme service systemd

---

## 📞 Support

**MediCare Industries**
- Zone Industrielle, Meknès, Maroc
- Email : contact@medicare-industries.ma

---

*Développé avec ❤️ pour MediCare Industries — StockPro v1.0*
