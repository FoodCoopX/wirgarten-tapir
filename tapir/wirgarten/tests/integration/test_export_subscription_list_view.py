import csv
import io

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import NOW, MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestExportSubscriptionListView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, NOW)

    def test_exportSubscriptionList_memberHasPhoneNumber_phoneNumberIsInCsv(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        member = MemberFactory.create(phone_number="+4915112345678")
        subscription = SubscriptionFactory.create(member=member, quantity=1)

        response = self.client.get(
            reverse("wirgarten:subscription_overview_export"),
            {"period": subscription.period.id},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        rows = list(csv.reader(io.StringIO(response.content.decode()), delimiter=";"))
        header = rows[0]
        self.assertIn("Telefon", header)
        phone_column = header.index("Telefon")
        self.assertIn("+4915112345678", [row[phone_column] for row in rows[1:]])

    def test_exportSubscriptionList_memberHasNoPhoneNumber_phoneColumnIsEmpty(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        member = MemberFactory.create(phone_number=None)
        subscription = SubscriptionFactory.create(member=member, quantity=1)

        response = self.client.get(
            reverse("wirgarten:subscription_overview_export"),
            {"period": subscription.period.id},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        rows = list(csv.reader(io.StringIO(response.content.decode()), delimiter=";"))
        phone_column = rows[0].index("Telefon")
        self.assertEqual("", rows[1][phone_column])
