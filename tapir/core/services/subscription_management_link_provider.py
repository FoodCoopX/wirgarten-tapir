from django.conf import settings
from django.urls import reverse

from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.mail.addressed_recipient import MailRecipient
from tapir.utils.services.tapir_cache import TapirCache


class SubscriptionManagementLinkProvider:
    TOKEN_NAME = "Newsletter - Verwaltungslink"

    @classmethod
    def get_link_for_recipient(cls, recipient: MailRecipient, cache: dict) -> str:
        return cls.build_link_for_address(address=recipient.email, cache=cache)

    @classmethod
    def build_link_for_address(cls, address: str, cache: dict) -> str:
        member_id = TapirCache.get_member_id_with_main_address(
            address=address, cache=cache
        )
        if member_id is not None:
            return settings.SITE_URL + reverse(
                "wirgarten:member_detail", args=[member_id]
            )

        return settings.SITE_URL + reverse(
            "core:subscription_management",
            args=[SubscriptionManagementTokenSigner.sign(address=address)],
        )
