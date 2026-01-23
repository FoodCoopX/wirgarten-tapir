from django.conf import settings
from django.urls import reverse
from tapir_mail.models import StaticSegmentRecipient, ExternalRecipient

from tapir.wirgarten.models import Member


class NewsletterManagementLinkProvider:
    @classmethod
    def get_newsletter_management_link(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ) -> str:
        if isinstance(recipient, Member):
            return cls.get_management_link_for_member(member=recipient)

        member = Member.objects.filter(email=recipient.email).first()
        if member is not None:
            return cls.get_management_link_for_member(member=member)

        external_recipient = ExternalRecipient.objects.filter(
            email=recipient.email
        ).first()
        if external_recipient is None:
            return ""

        return settings.SITE_URL + reverse(
            "tapir_mail:external_recipient_manager",
            args=[external_recipient.secret_key],
        )

    @classmethod
    def get_management_link_for_member(cls, member: Member):
        return reverse("wirgarten:member_detail", args=[member.id])
