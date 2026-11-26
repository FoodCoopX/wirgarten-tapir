from tapir.wirgarten.parameters import ParameterDefinitions
from django.urls import reverse

from tapir.mail.models import StaticSegment, StaticSegmentRecipient
from tapir.mail.registries import MailSegment
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.models import Member


class TestAvailableSegments(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self._login_as_admin()
        self.provider = lambda: {
            "Segment with metadata": MailSegment(
                get_queryset=Member.objects.all,
                label="Short label",
                description="Some description",
                group="Some group",
            ),
        }
        add_mail_segment_provider(self, self.provider)

    def get_segments_by_id(self):
        response = self.client.get(reverse("segment-available-segments"))
        self.assertStatusCode(response, 200)
        return {segment["id"]: segment for segment in response.json()["segments"]}

    def test_availableSegments_dynamicSegmentWithMetadata_returnsMetadata(self):
        segment = self.get_segments_by_id()["Segment with metadata"]

        self.assertEqual(
            {
                "id": "Segment with metadata",
                "type": "dynamic",
                "label": "Short label",
                "group": "Some group",
                "description": "Some description",
            },
            segment,
        )

    def test_availableSegments_staticSegmentWithSeveralRecipients_returnedOnce(self):
        static_segment = StaticSegment.objects.create(name="Static")
        for email in ["a@example.com", "b@example.com"]:
            StaticSegmentRecipient.objects.create(segment=static_segment, email=email)

        segments = self.client.get(reverse("segment-available-segments")).json()[
            "segments"
        ]

        static_entries = [
            segment for segment in segments if segment["id"] == static_segment.id
        ]
        self.assertEqual(1, len(static_entries))
        self.assertEqual("static", static_entries[0]["type"])
        self.assertEqual("Static", static_entries[0]["label"])

    def test_availableSegments_mailCategory_returnedAsCategory(self):
        category = MailCategoryFactory.create(name="Newsletter")

        segment = self.get_segments_by_id()[category.id]

        self.assertEqual("category", segment["type"])
        self.assertEqual("Newsletter", segment["label"])
        self.assertEqual("Kategorien", segment["group"])
