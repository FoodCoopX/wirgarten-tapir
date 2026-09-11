from django.apps import AppConfig


class BakeryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.bakery"

    def ready(self):
        from tapir.bakery import signals  # noqa: F401
