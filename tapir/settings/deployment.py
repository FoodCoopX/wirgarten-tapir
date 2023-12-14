import environ
import celery.schedules

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
            day_of_week="tuesday",
            minute=0,
            hour=3
            # once a week, Tuesday at 03:00
        ),
    },
    "export_pick_list_csv": {
        "task": "tapir.wirgarten.tasks.export_pick_list_csv",
        "schedule": celery.schedules.crontab(
            day_of_week="tuesday",
            minute=0,
            hour=3
            # once a week, Tuesday at 03:00
        ),
    },
    "export_payments_per_product_type": {
        "task": "tapir.wirgarten.tasks.export_payment_parts_csv",
        "schedule": celery.schedules.crontab(day_of_month=1, minute=0, hour=3),
    },
    "generate_member_numbers": {
        "task": "tapir.wirgarten.tasks.generate_member_numbers",
        "schedule": celery.schedules.crontab(day_of_month=1, minute=0, hour=3),
    },
}

# django-environ EMAIL_URL mechanism is a bit hairy with passwords with slashes in them, so use this instead
EMAIL_ENV = env("EMAIL_ENV", default="dev")
if EMAIL_ENV == "dev":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    EMAIL_HOST_SENDER = "dev@example.com"
elif EMAIL_ENV == "test":
    # Local SMTP
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
elif EMAIL_ENV == "prod":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env.str("EMAIL_HOST")
    EMAIL_HOST_SENDER = env.str("EMAIL_HOST_SENDER")
    EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")
    EMAIL_PORT = env.str("EMAIL_PORT", default=587)
    # the next 2 options are mutually exclusive!
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
    EMAIL_AUTO_BCC = env.str("EMAIL_AUTO_BCC", default=None)


# Crash emails will come from this address.
SERVER_EMAIL = env("SERVER_EMAIL", default="tapir@foodcoopx.de")

SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000")

KEYCLOAK_ADMIN_CONFIG = dict(
    SERVER_URL=env.str("KEYCLOAK_ADMIN_SERVER_URL", default="http://keycloak:8080"),
    PUBLIC_URL=env.str("KEYCLOAK_PUBLIC_URL", default="http://localhost:8080"),
    CLIENT_ID=env.str("KEYCLOAK_CLIENT_ID", default="tapir-backend"),
    FRONTEND_CLIENT_ID=env.str("KEYCLOAK_FRONTEND_CLIENT_ID", default="tapir-frontend"),
    REALM_NAME=env.str("KEYCLOAK_REALM_NAME", default="tapir"),
    CLIENT_SECRET_KEY=env.str("KEYCLOAK_ADMIN_CLIENT_SECRET_KEY", default="**********"),
)

CSP_FRAME_SRC = ["'self'", KEYCLOAK_ADMIN_CONFIG["PUBLIC_URL"]]
