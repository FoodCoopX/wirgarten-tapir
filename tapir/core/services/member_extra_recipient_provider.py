from tapir.configuration.parameter import get_parameter_value
from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys


class MemberExtraRecipientProvider:
    @classmethod
    def get_direct_mail_recipients(
        cls, member: Member, cache: dict
    ) -> list[AddressedRecipient]:
        if not get_parameter_value(
            ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ):
            return []

        return [
            AddressedRecipient(
                recipient=member,
                email=extra_email.email,
                token_overrides={
                    "first_name": extra_email.first_name,
                    "last_name": extra_email.last_name,
                },
            )
            for extra_email in TapirCache.get_confirmed_member_extra_emails_for_member(
                member_id=member.id, cache=cache
            )
            if extra_email.receives_direct_mails
        ]
