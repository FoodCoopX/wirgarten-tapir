from tapir.core.services.internal_recipient_manager import InternalRecipientManager
from tapir.mail.models import InternalRecipientCategoryRegistration
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestUpdateMemberRegistrations(TapirIntegrationTest):
    def test_updateMemberRegistrations_default_updatesOrCreatesTheSubmittedCategoriesAndKeepsTheOthers(
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

        InternalRecipientManager.update_member_registrations(
            member=member,
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
