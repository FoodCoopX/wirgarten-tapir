from django.db.models import QuerySet

from tapir.core.services.member_extra_recipient_provider import (
    MemberExtraRecipientProvider,
)
from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.mail.exceptions import TapirMailException
from tapir.mail.models import (
    MailCategory,
    MailCategoryMode,
    InternalRecipientCategoryRegistration,
)
from tapir.mail.registries import get_mail_segments
from tapir.wirgarten.models import Member


class MailCategoryRecipientResolver:
    @classmethod
    def resolve_recipients(
        cls, mail_category: MailCategory, cache: dict
    ) -> list[AddressedRecipient]:
        internal_recipients = cls.get_internal_segment(
            mail_category=mail_category,
        )

        external_recipients = mail_category.static_segment.recipients.all()

        return [
            *[
                AddressedRecipient.at_own_address(recipient)
                for recipient in [*internal_recipients, *external_recipients]
            ],
            *MemberExtraRecipientProvider.get_category_recipients(
                mail_category=mail_category, cache=cache
            ),
        ]

    @classmethod
    def get_internal_segment(cls, mail_category: MailCategory) -> QuerySet[Member]:
        if mail_category.dynamic_segment_name == "":
            return Member.objects.none()

        segment = get_mail_segments()[mail_category.dynamic_segment_name]()

        if mail_category.mode == MailCategoryMode.ALWAYS_ON:
            return segment

        registrations = InternalRecipientCategoryRegistration.objects.filter(
            mail_category=mail_category, member__isnull=False
        )

        if mail_category.mode == MailCategoryMode.OPTIONAL_DEFAULT_OFF:
            return segment.filter(
                id__in=registrations.filter(is_registered=True).values("member_id")
            )

        if mail_category.mode == MailCategoryMode.OPTIONAL_DEFAULT_ON:
            return segment.exclude(
                id__in=registrations.filter(is_registered=False).values("member_id")
            )

        raise TapirMailException(f"Unknown mail category mode: {mail_category.mode}")
