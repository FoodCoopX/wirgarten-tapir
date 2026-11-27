from django.core.exceptions import ValidationError

from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import MemberExtraEmail


class MemberExtraEmailConfirmationValidator:
    MAIN_ADDRESS_MESSAGE = "Diese Adresse ist bereits die Hauptadresse eines Mitglieds"
    OTHER_MEMBER_EXTRA_MESSAGE = "Diese Adresse ist bereits als zusätzliche Adresse eines anderen Mitglieds bestätigt"

    @classmethod
    def validate_address_is_free(cls, extra_email: MemberExtraEmail, cache: dict):
        if TapirCache.is_member_main_address(address=extra_email.email, cache=cache):
            raise ValidationError(cls.MAIN_ADDRESS_MESSAGE)

        owner = TapirCache.get_confirmed_member_extra_email_with_address(
            address=extra_email.email, cache=cache
        )
        if owner is not None and owner.id != extra_email.id:
            raise ValidationError(cls.OTHER_MEMBER_EXTRA_MESSAGE)
