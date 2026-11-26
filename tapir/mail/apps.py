from pathlib import Path
from typing import Callable

from django.apps import AppConfig

from tapir.mail.config import TransactionalTriggerKeys
from tapir.mail.service.triggers import register_trigger
from tapir.mail.triggers.time_trigger import TimeTrigger
from tapir.mail.triggers.transactional_trigger import TransactionalTrigger


class TapirMailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.mail"
    label = "tapir_mail"

    def ready(self):
        register_trigger(TimeTrigger)
        register_trigger(TransactionalTrigger)

        self.register_transactional_trigger(
            name="Mail-Kategorie-Registrierung - Bestätigung erforderlich",
            key=TransactionalTriggerKeys.MAIL_CATEGORY_REGISTRATION_CONFIRMATION_LINK,
            tokens={
                "Kategorie-Name": "category_name",
                "Bestätigungslink": "confirmation_link",
            },
            required=True,
        )

        self.register_transactional_trigger(
            name="Mail-Kategorie-Registrierung - Registrierung bestätigt",
            key=TransactionalTriggerKeys.MAIL_CATEGORY_REGISTRATION_CONFIRMED,
            tokens={
                "Kategorie-Name": "category_name",
                "Verwaltungslink": "management_link",
            },
            required=True,
        )

    @classmethod
    def register_transactional_trigger(
        cls, name: str, key: str, tokens: dict = None, required: bool | Callable = False
    ):
        TransactionalTrigger.register_action(
            name=name,
            key=key,
            required=required,
            tokens=tokens,
            default_content=cls.get_default_mail_content(key=key) if required else None,
        )

    @classmethod
    def get_default_mail_content(cls, key: str) -> str:
        file_path = Path(__file__).parent / f"email_drafts/{key}.mjml"
        with open(file_path, "r") as file:
            return file.read()
