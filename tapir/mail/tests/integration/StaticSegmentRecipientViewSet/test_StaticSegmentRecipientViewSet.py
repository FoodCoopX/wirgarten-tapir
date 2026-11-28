from django.urls import reverse

from tapir.mail.models import StaticSegment, StaticSegmentRecipient
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestStaticSegmentRecipientViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        self.segment = StaticSegment.objects.create(name="segment")

    def test_create_mixedCaseAddress_storesTheNormalisedAddress(self):
        response = self.client.post(
            reverse("staticsegmentrecipient-list"),
            data={"segment": self.segment.id, "email": " Static@Example.com"},
            content_type="application/json",
        )

        self.assertStatusCode(response, 201)
        self.assertEqual(
            "static@example.com", StaticSegmentRecipient.objects.get().email
        )

    def test_update_mixedCaseAddress_storesTheNormalisedAddress(self):
        recipient = StaticSegmentRecipient.objects.create(
            segment=self.segment, email="static@example.com"
        )

        response = self.client.patch(
            reverse("staticsegmentrecipient-detail", args=[recipient.id]),
            data={"email": "Other@Example.com"},
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        recipient.refresh_from_db()
        self.assertEqual("other@example.com", recipient.email)
