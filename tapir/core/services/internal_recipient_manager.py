from tapir.mail.models import (
    MailCategory,
    InternalRecipientCategoryRegistration,
    MailCategoryMode,
)
from tapir.mail.registries import get_mail_segments
from tapir.wirgarten.models import Member, MemberExtraEmail


class InternalRecipientManager:
    @classmethod
    def get_categories_for_member(cls, member: Member) -> list[MailCategory]:
        segment_registry = get_mail_segments()
        return [
            mail_category
            for mail_category in MailCategory.objects.exclude(
                dynamic_segment_name=""
            ).order_by("name")
            if segment_registry[mail_category.dynamic_segment_name]()
            .filter(id=member.id)
            .exists()
        ]

    @classmethod
    def is_member_registered_to_mail_category(
        cls, member: Member, mail_category: MailCategory
    ):
        if mail_category.mode == MailCategoryMode.ALWAYS_ON:
            return True

        registration = InternalRecipientCategoryRegistration.objects.filter(
            mail_category=mail_category, member=member
        ).first()
        if registration is not None:
            return registration.is_registered

        return mail_category.mode == MailCategoryMode.OPTIONAL_DEFAULT_ON

    @staticmethod
    def is_extra_email_registered_to_mail_category(
        extra_email: MemberExtraEmail, mail_category: MailCategory
    ) -> bool:
        registration = InternalRecipientCategoryRegistration.objects.filter(
            mail_category=mail_category, member_extra_email=extra_email
        ).first()
        if registration is not None:
            return registration.is_registered

        return mail_category.mode != MailCategoryMode.OPTIONAL_DEFAULT_OFF

    @staticmethod
    def update_member_registrations(
        member: Member, is_registered_by_category: dict[MailCategory, bool]
    ):
        for mail_category, is_registered in is_registered_by_category.items():
            InternalRecipientCategoryRegistration.objects.update_or_create(
                mail_category=mail_category,
                member=member,
                defaults={"is_registered": is_registered},
            )

    @staticmethod
    def update_extra_email_registrations(
        extra_email: MemberExtraEmail,
        is_registered_by_category: dict[MailCategory, bool],
    ):
        for mail_category, is_registered in is_registered_by_category.items():
            InternalRecipientCategoryRegistration.objects.update_or_create(
                mail_category=mail_category,
                member_extra_email=extra_email,
                defaults={"is_registered": is_registered},
            )
