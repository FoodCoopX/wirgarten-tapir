from django.conf import settings

from tapir.core.services.mailman.mailing_list_subscription_checker import (
    MailingListSubscriptionChecker,
)
from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient


class MailingListAddressMover:
    @staticmethod
    def move_subscriptions(old_email: str, new_email: str, cache: dict):
        if not settings.MAILING_LISTS_ENABLED:
            return

        for mailing_list in TapirMailmanClient.get_domain(cache=cache).lists:
            if MailingListSubscriptionChecker.is_member_subscribed_to_list(
                email=old_email, mailing_list=mailing_list
            ):
                if not MailingListSubscriptionChecker.is_member_subscribed_to_list(
                    email=new_email, mailing_list=mailing_list
                ):
                    mailing_list.subscribe(
                        address=new_email,
                        pre_verified=True,
                        pre_confirmed=True,
                        pre_approved=True,
                        send_welcome_message=False,
                    )
                mailing_list.unsubscribe(
                    email=old_email, pre_confirmed=True, pre_approved=True
                )
            for request in mailing_list.requests:
                if request["email"] == old_email:
                    mailing_list.discard_request(request_id=request["token"])
