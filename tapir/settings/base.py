"""
Django settings for tapir project.

Generated by 'django-admin startproject' using Django 3.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import os
from importlib import resources
from pathlib import Path

import environ

env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
ERROR_LOG_DIR = env.str("ERROR_LOG_DIR", default="error_logs")

ENABLE_SILK_PROFILING = False

# Application definition
INSTALLED_APPS = [
    # Must come before contrib.auth to let the custom templates be discovered for auth views
    "tapir.accounts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django_bootstrap5",
    "django_drf_filepond",
    "bootstrap_datepicker_plus",
    "tapir_mail",
    "tapir.core",
    "tapir.log",
    "tapir.utils",
    "tapir.wirgarten",
    "tapir.configuration",
    "tapir.deliveries",
    "tapir.generic_exports",
    "tapir.subscriptions",
    "tapir.coop",
    "tapir.pickup_locations",
    "django_tables2",
    "django_filters",
    "django_select2",  # For autocompletion in form fields
    "phonenumber_field",
    "localflavor",
    # TODO(Leon Handreke): Don't install in prod
    "django_extensions",
    "formtools",
    "tapir.wirgarten_site",
    "rest_framework",
    "drf_spectacular",
    "django_vite",
]

if ENABLE_SILK_PROFILING:
    INSTALLED_APPS.append("silk")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tapir.accounts.models.language_middleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "tapir.accounts.middleware.KeycloakMiddleware",
    "tapir.wirgarten.middleware.error.GlobalServerErrorHandlerMiddleware",
    "tapir.wirgarten.middleware.mailing.TapirMailPermissionMiddleware",
]

X_FRAME_OPTIONS = "ALLOWALL"
XS_SHARING_ALLOWED_METHODS = ["POST", "GET", "OPTIONS", "PUT", "DELETE"]

if ENABLE_SILK_PROFILING:
    MIDDLEWARE = ["silk.middleware.SilkyMiddleware"] + MIDDLEWARE

ROOT_URLCONF = "tapir.urls"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


def get_tapir_mail_template_dir():
    with resources.path("tapir_mail", "__ui__") as path:
        return str(path)


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "tapir/templates"),
            get_tapir_mail_template_dir(),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tapir.wsgi.application"


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/


def get_tapir_mail_static_dir():
    with resources.path("tapir_mail", "__static__") as path:
        return str(path)


STATIC_URL = "/static/"
STATIC_ROOT = "static"
STATICFILES_DIRS = [
    get_tapir_mail_static_dir(),
    "dist",
]

SELECT2_JS = "core/select2/4.0.13/js/select2.min.js"
SELECT2_CSS = "core/select2/4.0.13/css/select2.min.css"
SELECT2_I18N_PATH = "core/select2/4.0.13/js/i18n"

WEASYPRINT_BASEURL = "/"

AUTH_USER_MODEL = "accounts.TapirUser"
# LOGIN_REDIRECT_URL = "index"
LOGIN_URL = "login"

PHONENUMBER_DEFAULT_REGION = "DE"

LOCALE_PATHS = [os.path.join(BASE_DIR, "tapir/translations/locale")]

if ENABLE_SILK_PROFILING:
    SILKY_PYTHON_PROFILER = True
    SILKY_PYTHON_PROFILER_BINARY = True
    SILKY_META = True

# these are keycloak internal roles and will be filtered out automatically when fetching roles
KEYCLOAK_NON_TAPIR_ROLES = [
    "offline_access",
    "uma_authorization",
    "default-roles-tapir",
]

# The link above contains all settings
BOOTSTRAP_DATEPICKER_PLUS = {
    "options": {
        "locale": "de",
        "showClose": True,
        "showClear": True,
        "showTodayButton": True,
        "allowInputToggle": True,
    },
    "variant_options": {
        "date": {
            "format": "DD.MM.YYYY",
        },
        "datetime": {
            "format": "DD.MM.YYYY HH:mm",
        },
    },
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}
SPECTACULAR_SETTINGS = {"COMPONENT_SPLIT_REQUEST": True}

DJANGO_VITE = {
    "default": {
        "dev_mode": env.bool("DJANGO_VITE_DEBUG", default=False),
        "manifest_path": "./dist/manifest.json",
    }
}

# CORS
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
CORS_ALLOW_CREDENTIALS = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
