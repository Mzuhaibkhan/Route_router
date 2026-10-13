"""
Django settings for Route Radar / Fleet Weather Risk Engine.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')
raw_hosts = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,.onrender.com')
parsed_hosts = []
for h in raw_hosts.split(','):
    h = h.strip()
    if not h:
        continue
    # Django wildcard subdomains must start with '.' (e.g. '.onrender.com'), not '*.'
    if h.startswith('*.'):
        h = h[1:]
    parsed_hosts.append(h)

render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if render_hostname and render_hostname not in parsed_hosts:
    parsed_hosts.append(render_hostname)

# Always ensure .onrender.com is present for Render deployments
if '.onrender.com' not in parsed_hosts and '*' not in parsed_hosts:
    parsed_hosts.append('.onrender.com')

ALLOWED_HOSTS = parsed_hosts

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'

FRONTEND_DIST_DIR = BASE_DIR.parent / 'frontend' / 'dist'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [FRONTEND_DIST_DIR] if FRONTEND_DIST_DIR.exists() else [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = []
if (FRONTEND_DIST_DIR / 'assets').exists():
    STATICFILES_DIRS.append(FRONTEND_DIST_DIR / 'assets')

if FRONTEND_DIST_DIR.exists():
    WHITENOISE_ROOT = FRONTEND_DIST_DIR

# WhiteNoise storage: gzip + brotli compression and manifest caching
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Reverse Proxy / HTTPS Settings (Render deployment)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
NUM_PROXIES = 1

# CORS
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
CORS_ALLOWED_ORIGINS = [FRONTEND_URL] if FRONTEND_URL else []
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:5173,https://*.onrender.com').split(',')
    if origin.strip()
]

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'EXCEPTION_HANDLER': 'api.exceptions.custom_exception_handler',
    'NUM_PROXIES': 1,
}

# Caching
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'fleet-radar-cache',
        'TIMEOUT': 3600,  # 1 hour default
    }
}

# External API Keys
ORS_API_KEY = os.getenv('ORS_API_KEY', '')
