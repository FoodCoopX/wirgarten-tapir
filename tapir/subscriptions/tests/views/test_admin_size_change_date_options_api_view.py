import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAdminSizeChangeDateOptionsApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2030, month=1, day=1)
        )
        cls.next_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2031, month=1, day=1)
        )

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2030, month=6, day=1))

    def _get(self, subscription_id: str):
        return self.client.get(
            reverse("subscriptions:admin_size_change_date_options"),
            {"subscription_id": subscription_id},
        )

    def test_get_normalMember_returns403(self):
        subscription = SubscriptionFactory.create(period=self.growing_period)
        self.client.force_login(subscription.member)

        response = self._get(subscription_id=subscription.id)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_admin_returnsOptionsForTheSubscription(self):
        self._login_as_admin()
        subscription = SubscriptionFactory.create(
            member=MemberFactory.create(), period=self.growing_period
        )

        response = self._get(subscription_id=subscription.id)

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            {"date": "2031-01-01", "enabled": True}, data["next_period_start"]
        )
        self.assertEqual("2030-06-03", data["weeks"][0]["date"])
        self.assertEqual("2030-12-30", data["weeks"][-1]["date"])
        self.assertIn("enabled", data["next_possible_start"])
