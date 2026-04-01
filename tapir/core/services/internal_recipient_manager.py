from tapir_mail.models import (
    MailCategory,
    InternalRecipientCategoryRegistration,
    MailCategoryMode,
)

from tapir.wirgarten.models import Member


class InternalRecipientManager:
    @classmethod
    def is_member_registered_to_mail_category(
        cls, member: Member, mail_category: MailCategory
    ):
        if mail_category.mode == MailCategoryMode.ALWAYS_ON:
            return True

        registration = InternalRecipientCategoryRegistration.objects.filter(
            mail_category=mail_category, internal_recipient_id=member.id
        ).first()
        if registration is not None:
            return registration.is_registered

        return mail_category.mode == MailCategoryMode.OPTIONAL_DEFAULT_ON
