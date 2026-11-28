from django.conf import settings

from tapir.core.services.mailman.mailing_list_subscription_checker import (
    MailingListSubscriptionChecker,
)
from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient
from tapir.mail.models import ExternalRecipient
from tapir.wirgarten.models import Member, MemberExtraEmail


class MailingListUnsubscriber:
    @classmethod
    def unsubscribe_if_address_unused(cls, email: str, cache: dict):
        if not settings.MAILING_LISTS_ENABLED:
            return
        if cls._is_address_still_in_use(email=email):
            return

        for mailing_list in TapirMailmanClient.get_domain(cache=cache).lists:
            if MailingListSubscriptionChecker.is_member_subscribed_to_list(
                email=email, mailing_list=mailing_list
            ):
                mailing_list.unsubscribe(
                    email=email, pre_confirmed=True, pre_approved=True
                )
            for request in mailing_list.requests:
                if request["email"] == email:
                    mailing_list.discard_request(request_id=request["token"])

    @staticmethod
    def _is_address_still_in_use(email: str) -> bool:
        return (
            Member.objects.filter(email=email).exists()
            or MemberExtraEmail.objects.filter(
                email=email, confirmed_on__isnull=False
            ).exists()
            or ExternalRecipient.objects.filter(email=email).exists()
        )
