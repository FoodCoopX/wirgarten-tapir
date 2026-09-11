from tapir_mail.models import StaticSegmentRecipient

from tapir.utils.user_utils import UserUtils
from tapir.wirgarten.models import Member


class MemberMailTokenService:
    @classmethod
    def get_post_address(cls, recipient: Member | StaticSegmentRecipient, cache: dict):
        if not isinstance(recipient, Member):
            return ""

        return UserUtils.build_display_address(
            street=recipient.street,
            street_2=recipient.street_2,
            postcode=recipient.postcode,
            city=recipient.city,
        )
