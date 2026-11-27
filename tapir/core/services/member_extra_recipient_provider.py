from tapir.configuration.parameter import get_parameter_value
from tapir.core.services.subscription_management_link_provider import (
    SubscriptionManagementLinkProvider,
)
from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.mail.models import (
    InternalRecipientCategoryRegistration,
    MailCategory,
    MailCategoryMode,
)
from tapir.mail.registries import get_mail_segments
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, MemberExtraEmail
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
            cls._build_addressed_recipient(
                extra_email=extra_email, member=member, cache=cache
            )
            for extra_email in TapirCache.get_confirmed_member_extra_emails_for_member(
                member_id=member.id, cache=cache
            )
            if extra_email.receives_direct_mails
        ]

    @classmethod
    def get_category_recipients(
        cls, mail_category: MailCategory, cache: dict
    ) -> list[AddressedRecipient]:
        if mail_category.dynamic_segment_name == "" or not get_parameter_value(
            ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ):
            return []

        segment = get_mail_segments()[mail_category.dynamic_segment_name]()
        extra_emails = MemberExtraEmail.objects.filter(
            member_id__in=segment.values_list("id", flat=True),
            confirmed_on__isnull=False,
        )
        registrations = InternalRecipientCategoryRegistration.objects.filter(
            mail_category=mail_category, member_extra_email__isnull=False
        )
        # ALWAYS_ON counts as default on: mandatory mails still reach the main address.
        if mail_category.mode == MailCategoryMode.OPTIONAL_DEFAULT_OFF:
            extra_emails = extra_emails.filter(
                id__in=registrations.filter(is_registered=True).values(
                    "member_extra_email_id"
                )
            )
        else:
            extra_emails = extra_emails.exclude(
                id__in=registrations.filter(is_registered=False).values(
                    "member_extra_email_id"
                )
            )

        return [
            cls._build_addressed_recipient(
                extra_email=extra_email, member=extra_email.member, cache=cache
            )
            for extra_email in extra_emails.select_related("member").order_by("email")
        ]

    @staticmethod
    def _build_addressed_recipient(
        extra_email: MemberExtraEmail, member: Member, cache: dict
    ) -> AddressedRecipient:
        return AddressedRecipient(
            recipient=member,
            email=extra_email.email,
            token_overrides={
                "first_name": extra_email.first_name,
                "last_name": extra_email.last_name,
                SubscriptionManagementLinkProvider.TOKEN_NAME: SubscriptionManagementLinkProvider.build_link_for_address(
                    address=extra_email.email, cache=cache
                ),
            },
        )
