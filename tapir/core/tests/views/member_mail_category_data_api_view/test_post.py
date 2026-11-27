from django.urls import reverse
from rest_framework import status

from tapir.mail.models import InternalRecipientCategoryRegistration
from tapir.mail.tests.factories import MailCategoryFactory, MailSegmentFactory
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberMailCategoryDataApiViewPost(TapirIntegrationTest):
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
        self.member = MemberFactory.create()
        self.client.force_login(self.member)

    def test_post_default_updatesTheSubmittedCategoriesAndKeepsTheOthers(self):
        submitted_category = MailCategoryFactory.create(
            dynamic_segment_name=self.SEGMENT_WITH_MEMBER
        )
        category_outside_segment = MailCategoryFactory.create(
            dynamic_segment_name=self.SEGMENT_WITHOUT_MEMBER
        )
        for category in [submitted_category, category_outside_segment]:
            InternalRecipientCategoryRegistration.objects.create(
                member=self.member, mail_category=category, is_registered=True
            )

        response = self._post(categories_registered_to={submitted_category.id: False})

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {submitted_category.id: False, category_outside_segment.id: True},
            dict(
                InternalRecipientCategoryRegistration.objects.filter(
                    member=self.member
                ).values_list("mail_category_id", "is_registered")
            ),
        )

    def test_post_categoryOutsideTheMemberSegments_returns400(self):
        category_outside_segment = MailCategoryFactory.create(
            dynamic_segment_name=self.SEGMENT_WITHOUT_MEMBER
        )

        response = self._post(
            categories_registered_to={category_outside_segment.id: True}
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            [
                f"Diese Mail-Kategorien sind nicht verfügbar: {category_outside_segment.id}"
            ],
            response.json(),
        )
        self.assertFalse(InternalRecipientCategoryRegistration.objects.exists())

    def _post(self, categories_registered_to: dict[str, bool]):
        return self.client.post(
            reverse("core:member_mail_category_data"),
            data={
                "member_id": self.member.id,
                "categories_registered_to": categories_registered_to,
            },
            content_type="application/json",
        )
