from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.accounts"

    def ready(self) -> None:
        # Required for DRF spectacular
        # noinspection PyUnresolvedReferences
        from tapir.accounts.drf_authentication import (
            DrfForwardAuthenticationScheme,
        )  # noqa: E402
