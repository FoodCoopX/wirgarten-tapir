from tapir.mail.models import (
    MailCategory,
    StaticSegmentRecipient,
    ExternalRecipient,
    ExternalRecipientConfirmation,
)


class ExternalRecipientManager:
    @staticmethod
    def is_email_address_registered_to_category(
        mail_category: MailCategory, email: str
    ):
        return StaticSegmentRecipient.objects.filter(
            segment_id=mail_category.static_segment_id,
            email=email,
        ).exists()

    @classmethod
    def register_external_recipient_to_category(
        cls, mail_category: MailCategory, external_recipient: ExternalRecipient
    ):
        cls.register_static_recipient_to_category(
            mail_category=mail_category,
            email=external_recipient.email,
            first_name=external_recipient.first_name,
        )

    @classmethod
    def register_static_recipient_to_category(
        cls, mail_category: MailCategory, email: str, first_name: str
    ):
        StaticSegmentRecipient.objects.get_or_create(
            segment_id=mail_category.static_segment_id,
            email=email,
            defaults={"first_name": first_name},
        )

    @classmethod
    def remove_external_recipient_from_category(
        cls, mail_category: MailCategory, external_recipient: ExternalRecipient
    ):
        cls.remove_static_recipient_from_category(
            mail_category=mail_category, email=external_recipient.email
        )
        ExternalRecipientConfirmation.objects.filter(
            mail_category=mail_category, external_recipient=external_recipient
        ).delete()

    @classmethod
    def remove_static_recipient_from_category(
        cls, mail_category: MailCategory, email: str
    ):
        StaticSegmentRecipient.objects.filter(
            segment_id=mail_category.static_segment_id,
            email=email,
        ).delete()
