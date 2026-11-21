import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAdminSubscriptionAdditionDateOptionsApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)
        GrowingPeriodFactory.create(start_date=datetime.date(year=2030, month=1, day=1))
        GrowingPeriodFactory.create(start_date=datetime.date(year=2031, month=1, day=1))
        cls.product_type = ProductTypeFactory.create()

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2030, month=6, day=1))

    def _get(self):
        return self.client.get(
            reverse("subscriptions:admin_subscription_addition_date_options"),
            {"product_type_id": self.product_type.id},
        )

    def test_get_normalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self._get()

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_admin_returnsOptionsUntilEndOfNextPeriod(self):
        self._login_as_admin()

        response = self._get()

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            {"date": "2031-01-01", "enabled": True}, data["next_period_start"]
        )
        self.assertEqual("2030-06-03", data["weeks"][0]["date"])
        self.assertEqual("2031-12-29", data["weeks"][-1]["date"])
