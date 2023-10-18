from django.apps import AppConfig


class WirgartenConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.wirgarten"

    def ready(self) -> None:
        try:
            from .tapirmail import configure_mail_module

            configure_mail_module()
        except Exception as e:
            print(e)
            pass
