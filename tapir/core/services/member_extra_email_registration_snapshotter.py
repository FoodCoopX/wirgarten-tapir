from django.conf import settings
from django.db import transaction

from tapir.core.services.active_member_provider import ActiveMemberProvider
from tapir.core.services.internal_recipient_manager import InternalRecipientManager
from tapir.core.services.mailman.mailing_list_subscription_checker import (
    MailingListSubscriptionChecker,
)
from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient
from tapir.mail.models import InternalRecipientCategoryRegistration
from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.utils import get_now


class MemberExtraEmailRegistrationSnapshotter:
    @classmethod
    def snapshot(cls, extra_email: MemberExtraEmail, cache: dict):
        cls._snapshot_mail_categories(extra_email=extra_email)

        if (
            settings.MAILING_LISTS_ENABLED
            and ActiveMemberProvider.get_active_members(
                reference_datetime=get_now(cache=cache), cache=cache
            )
            .filter(id=extra_email.member_id)
            .exists()
        ):
            transaction.on_commit(
                lambda: cls._snapshot_mailing_lists(
                    extra_email_address=extra_email.email,
                    main_address=extra_email.member.email,
                    cache=cache,
                ),
                robust=True,
            )

    @staticmethod
    def _snapshot_mail_categories(extra_email: MemberExtraEmail):
        InternalRecipientCategoryRegistration.objects.bulk_create(
            [
                InternalRecipientCategoryRegistration(
                    member_extra_email=extra_email,
                    mail_category=mail_category,
                    is_registered=InternalRecipientManager.is_member_registered_to_mail_category(
                        member=extra_email.member, mail_category=mail_category
                    ),
                )
                for mail_category in InternalRecipientManager.get_categories_for_member(
                    member=extra_email.member
                )
            ]
        )

    @staticmethod
    def _snapshot_mailing_lists(
        extra_email_address: str, main_address: str, cache: dict
    ):
        for mailing_list in TapirMailmanClient.get_domain(cache=cache).lists:
            if not MailingListSubscriptionChecker.is_member_subscribed_to_list(
                email=main_address, mailing_list=mailing_list
            ):
                continue
            if MailingListSubscriptionChecker.is_member_subscribed_to_list(
                email=extra_email_address, mailing_list=mailing_list
            ) or MailingListSubscriptionChecker.is_member_waiting_for_confirmation(
                email=extra_email_address, mailing_list=mailing_list
            ):
                continue

            mailing_list.subscribe(
                address=extra_email_address,
                pre_verified=True,
                pre_confirmed=True,
                pre_approved=True,
                send_welcome_message=False,
            )
