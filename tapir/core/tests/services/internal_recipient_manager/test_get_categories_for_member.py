from tapir.core.services.internal_recipient_manager import InternalRecipientManager
from tapir.mail.tests.factories import MailCategoryFactory, MailSegmentFactory
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetCategoriesForMember(TapirIntegrationTest):
    SEGMENT_WITH_MEMBER = "segment_with_member"
    SEGMENT_WITHOUT_MEMBER = "segment_without_member"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        add_mail_segment_provider(
            self,
            lambda: {
                self.SEGMENT_WITH_MEMBER: MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                ),
                self.SEGMENT_WITHOUT_MEMBER: MailSegmentFactory.build(
                    get_queryset=Member.objects.none
                ),
            },
        )

    def test_getCategoriesForMember_default_returnsCategoriesWhoseDynamicSegmentContainsTheMemberSortedByName(
        self,
    ):
        member = MemberFactory.create()
        category_b = MailCategoryFactory.create(
            name="B", dynamic_segment_name=self.SEGMENT_WITH_MEMBER
        )
        category_a = MailCategoryFactory.create(
            name="A", dynamic_segment_name=self.SEGMENT_WITH_MEMBER
        )
        MailCategoryFactory.create(
            name="C", dynamic_segment_name=self.SEGMENT_WITHOUT_MEMBER
        )
        MailCategoryFactory.create(name="D", dynamic_segment_name="")

        result = InternalRecipientManager.get_categories_for_member(member=member)

        self.assertEqual([category_a, category_b], result)
