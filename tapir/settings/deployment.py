import datetime
import os

import celery.schedules
import environ

from tapir.settings.base import BASE_DIR

env = environ.Env()

TAPIR_VERSION = env.str("TAPIR_VERSION", default="dev")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str(
    "SECRET_KEY", default="fl%20e9dbkh4mosi5$i$!5&+f^ic5=7^92hrchl89x+)k0ctsn"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)
if not DEBUG:
    print(
        f"Tapir Version: {TAPIR_VERSION}"
        if TAPIR_VERSION
        else "\033[93m>>> WARNING: TAPIR_VERSION is not set, cache busting will not work!\033[0m"
    )


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    "default": env.db(
        "DATABASE_CONNECTION", default="postgresql://tapir:tapir@db:5432/tapir"
    ),
}

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://redis:6379")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="redis://redis:6379")
CELERY_BEAT_SCHEDULE = {
    "execute_scheduled_tasks": {
        "task": "tapir.wirgarten.tasks.execute_scheduled_tasks",
        "schedule": celery.schedules.crontab(
            minute=[5],
        ),  # every hour
    },
    "export_supplier_list_csv": {
        "task": "tapir.wirgarten.tasks.export_supplier_list_csv",
        "schedule": celery.schedules.crontab(
            minute=0,
            hour=3,
        ),
    },
    "export_pick_list_csv": {
        "task": "tapir.wirgarten.tasks.export_pick_list_csv",
        "schedule": celery.schedules.crontab(
            minute=0,
            hour=4,
        ),
    },
    "export_payments_per_product_type": {
        "task": "tapir.wirgarten.tasks.export_payment_parts_csv",
        "schedule": celery.schedules.crontab(day_of_month="1", minute="0", hour="3"),
    },
    "generate_member_numbers": {
        "task": "tapir.wirgarten.tasks.generate_member_numbers",
        "schedule": celery.schedules.crontab(minute="0", hour="3"),
    },
    "resolve_segment_and_create_email_dispatches_task": {
        "task": "tapir_mail.tasks.resolve_segment_and_create_email_dispatches_task",
        "schedule": datetime.timedelta(minutes=1),
    },
    "send_email_dispatch_batch_task": {
        "task": "tapir_mail.tasks.send_email_dispatch_batch_task",
        "schedule": datetime.timedelta(minutes=1),
    },
    "check_email_bounces": {
        "task": "tapir_mail.tasks.check_email_bounces",
        "schedule": datetime.timedelta(minutes=1),
    },
    "do_automated_exports": {
        "task": "tapir.generic_exports.tasks.do_automated_exports",
        "schedule": datetime.timedelta(minutes=1),
    },
    "automatic_subscription_renewal": {
        "task": "tapir.subscriptions.tasks.automatic_subscription_renewal",
        "schedule": celery.schedules.crontab(hour="2", minute="0"),
    },
    "automatic_confirmation": {
        "task": "tapir.subscriptions.tasks.automatic_confirmation_subscriptions_and_share_purchases",
        "schedule": celery.schedules.crontab(hour="0", minute="30"),
    },
}

EMAIL_DISPATCH_BATCH_SIZE = (
    200  # job runs 1x/minute --> 200 * 60 = 12,000 emails per hour maximum
)

# if True, email will not be sent and set to ERROR if it contains unknown tokens. If False, unknown tokens are just stripped and ignored.
EMAIL_TOKENS_STRICT_VALIDATION = True

EMAIL_ENV = env("EMAIL_ENV", default="dev")
EMAIL_PORT_IMAP = env.str("EMAIL_PORT_IMAP", default=993)
EMAIL_PORT = env.str("EMAIL_PORT", default=587)
# the next 2 options are mutually exclusive!
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
if EMAIL_ENV == "dev":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    EMAIL_HOST = "email_host"
    EMAIL_HOST_USER = "email_host_user"
    EMAIL_HOST_PASSWORD = "email_host_password"
    EMAIL_HOST_SENDER = "test_host_sender@example.com"
    EMAIL_BOUNCE_ADDRESS = "bounce@example.com"
    EMAIL_HOST_SENDER_NAME = "Test host sender"
elif EMAIL_ENV == "test":
    # Local SMTP
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
elif EMAIL_ENV == "prod":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env.str("EMAIL_HOST")
    EMAIL_HOST_SENDER = env.str(
        "EMAIL_HOST_SENDER"
    )  # The address that the client will see
    EMAIL_HOST_SENDER_NAME = env.str("EMAIL_HOST_SENDER_NAME")
    EMAIL_BOUNCE_ADDRESS = env.str(
        "EMAIL_BOUNCE_ADDRESS"
    )  # The address that the mail will be sent from
    EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")
    EMAIL_AUTO_BCC = env.str("EMAIL_AUTO_BCC", default=None)


# Crash emails will come from this address.
SERVER_EMAIL = env("SERVER_EMAIL", default="tapir@foodcoopx.de")

SITE_URL = env("SITE_URL", default="http://localhost:8000")

KEYCLOAK_ADMIN_CONFIG = dict(
    SERVER_URL=env.str("KEYCLOAK_ADMIN_SERVER_URL", default="http://keycloak:8080"),
    PUBLIC_URL=env.str("KEYCLOAK_PUBLIC_URL", default="http://localhost:8080"),
    CLIENT_ID=env.str("KEYCLOAK_CLIENT_ID", default="tapir-backend"),
    FRONTEND_CLIENT_ID=env.str("KEYCLOAK_FRONTEND_CLIENT_ID", default="tapir-frontend"),
    REALM_NAME=env.str("KEYCLOAK_REALM_NAME", default="tapir"),
    CLIENT_SECRET_KEY=env.str("KEYCLOAK_ADMIN_CLIENT_SECRET_KEY", default="**********"),
)

CSP_FRAME_SRC = ["'self'", KEYCLOAK_ADMIN_CONFIG["PUBLIC_URL"]]


# Tapir Mail
DJANGO_DRF_FILEPOND_UPLOAD_TMP = os.path.join(BASE_DIR, "filepond_temp_uploads")
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = os.path.join(BASE_DIR, "filepond_stored_uploads")

MJML_BACKEND_MODE = "cmd"
MJML_EXEC_CMD = [
    "mjml",
    "--config.juicePreserveTags",
    "true",
    "--config.validationLevel",
    "skip",
    "--config.minify",
    "true",
    "--config.beautify",
    "false",
    "--config.keepComments",
    "false",
    "--config.minifyOptions",
    '{"removeComments": true}',
]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CELERY_BROKER_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

TAPIR_MAIL_PATH = "/tapirmail"
TAPIRMAIL_REACT_APP_API_ROOT = SITE_URL + TAPIR_MAIL_PATH
TAPIRMAIL_REACT_APP_BASENAME = TAPIR_MAIL_PATH

if DEBUG:
    CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", SITE_URL]

SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "APPS": [
            {
                "provider_id": "keycloak",
                "name": "Keycloak",
                "client_id": KEYCLOAK_ADMIN_CONFIG["CLIENT_ID"],
                "secret": KEYCLOAK_ADMIN_CONFIG["CLIENT_SECRET_KEY"],
                "settings": {
                    "server_url": f"{KEYCLOAK_ADMIN_CONFIG["SERVER_URL"]}/realms/{KEYCLOAK_ADMIN_CONFIG["REALM_NAME"]}/.well-known/openid-configuration",
                },
            }
        ]
    }
}

if DEBUG:
    INTERNAL_IPS = ["127.0.0.1"]
