from tapir.configuration.parameter import get_parameter_value
from tapir.core.services.subscription_management_link_provider import (
    SubscriptionManagementLinkProvider,
)
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.mail.models import ExternalRecipient
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)
from tapir.wirgarten.mail_events import Events
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.parameter_keys import ParameterKeys


class SubscriptionManagementLinkSender:
    @classmethod
    def send_link(cls, address: str, cache: dict):
        if TapirCache.is_member_main_address(address=address, cache=cache):
            return

        owner = cls._find_owner(address=address, cache=cache)
        if owner is None:
            return

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.SUBSCRIPTION_MANAGEMENT_LINK,
                token_data={
                    "management_link": SubscriptionManagementLinkProvider.build_link_for_address(
                        address=address, cache=cache
                    ),
                    "validity": f"{SubscriptionManagementTokenSigner.VALIDITY_HOURS} Stunden",
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=address, first_name=owner.first_name, last_name=""
                ),
            )
        )

    @staticmethod
    def _find_owner(
        address: str, cache: dict
    ) -> MemberExtraEmail | ExternalRecipient | None:
        if get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ):
            extra_email = MemberExtraEmail.objects.filter(
                email=address, confirmed_on__isnull=False
            ).first()
            if extra_email is not None:
                return extra_email

        return ExternalRecipient.objects.filter(email=address).first()
