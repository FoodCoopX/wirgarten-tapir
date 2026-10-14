from django.apps import AppConfig
from tapir_mail.config import ExternalConfig

from tapir.wirgarten.parameter_keys import ParameterKeys


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.core"

    def ready(self) -> None:
        ExternalConfig.MASS_MAIL_BCC_PROVIDER = lambda: self.get_bcc_if_enabled(
            ParameterKeys.BCC_MAIL_MODULE_MASS_MAILS
        )
        ExternalConfig.TRANSACTIONAL_MAIL_BCC_PROVIDER = (
            lambda: self.get_bcc_if_enabled(
                ParameterKeys.BCC_MAIL_MODULE_TRANSACTIONAL_MAILS
            )
        )

    @classmethod
    def get_bcc_if_enabled(cls, key: str) -> str | None:
        from tapir.configuration.parameter import get_parameter_value

        cache = {}
        if not get_parameter_value(
            ParameterKeys.ENABLE_BCC_FOR_MAIL_MODULE, cache=cache
        ):
            return None
        return get_parameter_value(key, cache=cache)
