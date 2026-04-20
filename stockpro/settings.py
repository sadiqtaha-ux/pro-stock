"""
StockPro - Configuration Django 4.2
MediCare Industries - Meknès, Maroc
"""

from pathlib import Path
from decouple import config, Csv

# ============================================================
# CHEMINS DE BASE
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# SÉCURITÉ
# ============================================================
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ============================================================
# APPLICATIONS INSTALLÉES
# ============================================================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    'django_filters',
    'import_export',
    'guardian',
    'django_celery_beat',
    'django_celery_results',
    'debug_toolbar',
]

LOCAL_APPS = [
    'core.apps.CoreConfig',
    'produits.apps.ProduitsConfig',
    'mouvements.apps.MouvementsConfig',
    'approvisionnement.apps.ApprovisionnementConfig',
    'dashboard.apps.DashboardConfig',
    'magasin.apps.MagasinConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ============================================================
# MIDDLEWARES
# ============================================================
MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware personnalisé
    'core.middleware.ActivityLogMiddleware',
    'core.middleware.StockAlertMiddleware',
]

ROOT_URLCONF = 'stockpro.urls'

# ============================================================
# TEMPLATES
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Context processors personnalisés
                'core.context_processors.company_info',
                'core.context_processors.stock_alerts_count',
                'core.context_processors.navigation_perms',
            ],
        },
    },
]

WSGI_APPLICATION = 'stockpro.wsgi.application'

# ============================================================
# BASE DE DONNÉES
# PostgreSQL en production, SQLite optionnel en dev
# ============================================================
USE_SQLITE = config('USE_SQLITE', default=False, cast=bool)

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='stockpro_db'),
            'USER': config('DB_USER', default='stockpro_user'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }

# ============================================================
# AUTHENTIFICATION
# ============================================================
AUTH_USER_MODEL = 'core.Utilisateur'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================
# BACKENDS D'AUTHENTIFICATION
# ============================================================
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
]

LOGIN_URL = 'core:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'core:login'

# ============================================================
# INTERNATIONALISATION - MAROC
# ============================================================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Casablanca'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ============================================================
# FICHIERS STATIQUES
# ============================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================
# FICHIERS MÉDIA
# ============================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# CLEF PRIMAIRE PAR DÉFAUT
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# CRISPY FORMS - Bootstrap 5
# ============================================================
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

# ============================================================
# CELERY - Tâches asynchrones
# ============================================================
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Casablanca'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ============================================================
# CACHE - Redis
# ============================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/0'),
        'TIMEOUT': 300,  # 5 minutes
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}

# ============================================================
# EMAIL
# ============================================================
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER', default='noreply@medicare-industries.ma')

# ============================================================
# DJANGO DEBUG TOOLBAR
# ============================================================
INTERNAL_IPS = ['127.0.0.1']

# ============================================================
# LOGGING
# ============================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'stockpro.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'stockpro': {
            'handlers': ['console', 'file'],
            'level': config('LOG_LEVEL', default='DEBUG'),
            'propagate': False,
        },
    },
}

# ============================================================
# INFORMATIONS ENTREPRISE - MediCare Industries
# ============================================================
COMPANY_INFO = {
    'nom': config('COMPANY_NAME', default='MediCare Industries'),
    'adresse': config('COMPANY_ADDRESS', default='Zone Industrielle'),
    'telephone': config('COMPANY_PHONE', default='+212 535-XXXXXX'),
    'email': config('COMPANY_EMAIL', default='contact@medicare-industries.ma'),
    'ice': config('COMPANY_ICE', default='000000000000000'),
    'rc': config('COMPANY_RC', default='12345'),
    'ville': 'Meknès',
    'pays': 'Maroc',
    'devise': 'MAD',
    'symbole_devise': 'DH',
}

# ============================================================
# PARAMÈTRES STOCKPRO SPÉCIFIQUES
# ============================================================
STOCKPRO_SETTINGS = {
    # Seuils d'alerte par défaut
    'SEUIL_ALERTE_STOCK': 20,       # % du stock maximum
    'SEUIL_CRITIQUE_STOCK': 10,     # % du stock maximum
    'JOURS_PEREMPTION_ALERTE': 90,  # Jours avant péremption à alerter
    # Méthodes d'approvisionnement
    'METHODES_APPRO': [
        'REAPPRO_FIXE',
        'POINT_COMMANDE',
        'RECOMPLETEMENT',
        'MRP',
    ],
    # Pagination
    'ITEMS_PAR_PAGE': 25,
}
