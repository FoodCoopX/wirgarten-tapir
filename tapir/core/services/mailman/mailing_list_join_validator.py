from rest_framework.exceptions import ValidationError

from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.wirgarten.utils import get_now


class MailingListJoinValidator:
    FORMER_MEMBER_MESSAGE = "Diese Adresse gehört zu einem ehemaligen Mitglied und kann keiner Mailing-Liste beitreten"

    @classmethod
    def validate_address_can_join(cls, address: str, cache: dict):
        if FormerMemberAddressProvider.is_former_member_address(
            address=address, reference_datetime=get_now(cache=cache), cache=cache
        ):
            raise ValidationError(cls.FORMER_MEMBER_MESSAGE)
