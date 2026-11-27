from django.utils import timezone

from tapir.core.services.internal_recipient_manager import InternalRecipientManager
from tapir.mail.models import InternalRecipientCategoryRegistration
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestUpdateRegistrations(TapirIntegrationTest):
    def test_updateRegistrations_member_updatesOrCreatesTheSubmittedCategoriesAndKeepsTheOthers(
        self,
    ):
        member = MemberFactory.create()
        existing_category, new_category, other_category = (
            MailCategoryFactory.create_batch(3)
        )
        for category in [existing_category, other_category]:
            InternalRecipientCategoryRegistration.objects.create(
                member=member, mail_category=category, is_registered=True
            )

        InternalRecipientManager.update_registrations(
            recipient=member,
            is_registered_by_category={existing_category: False, new_category: True},
        )

        self.assertEqual(
            {
                existing_category.id: False,
                new_category.id: True,
                other_category.id: True,
            },
            dict(
                InternalRecipientCategoryRegistration.objects.filter(
                    member=member
                ).values_list("mail_category_id", "is_registered")
            ),
        )

    def test_updateRegistrations_extraEmail_updatesOrCreatesTheExtraRegistrations(
        self,
    ):
        extra_email = MemberExtraEmailFactory.create(confirmed_on=timezone.now())
        existing_category, new_category = MailCategoryFactory.create_batch(2)
        InternalRecipientCategoryRegistration.objects.create(
            member_extra_email=extra_email,
            mail_category=existing_category,
            is_registered=True,
        )
        InternalRecipientCategoryRegistration.objects.create(
            member=extra_email.member,
            mail_category=existing_category,
            is_registered=True,
        )

        InternalRecipientManager.update_registrations(
            recipient=extra_email,
            is_registered_by_category={existing_category: False, new_category: True},
        )

        self.assertEqual(
            {existing_category.id: False, new_category.id: True},
            dict(
                InternalRecipientCategoryRegistration.objects.filter(
                    member_extra_email=extra_email
                ).values_list("mail_category_id", "is_registered")
            ),
        )
        self.assertTrue(
            InternalRecipientCategoryRegistration.objects.get(
                member=extra_email.member
            ).is_registered
        )
