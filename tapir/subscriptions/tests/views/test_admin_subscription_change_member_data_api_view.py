import datetime

from django.urls import reverse
from rest_framework import status

from tapir.payments.models import MemberPaymentRhythm
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAdminSubscriptionChangeMemberDataApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2030, month=1, day=1)
        )

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2030, month=6, day=1))

    def _get(self, member_id: str):
        return self.client.get(
            reverse("subscriptions:admin_subscription_change_member_data"),
            {"member_id": member_id},
        )

    def test_get_normalMemberAsksForThemselves_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self._get(member_id=member.id)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_admin_returnsMemberSubscriptionUnitsAndPrerequisites(self):
        self._login_as_admin()
        member = MemberFactory.create(first_name="Erika", last_name="Mustermann")
        subscription = SubscriptionFactory.create(
            member=member, period=self.growing_period, quantity=2
        )

        response = self._get(member_id=member.id)

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual("Erika Mustermann", data["member"]["display_name"])
        self.assertEqual(
            [(subscription.id, 1), (subscription.id, 2)],
            [
                (unit["subscription_id"], unit["unit_number"])
                for unit in data["subscription_units"]
            ],
        )
        self.assertEqual("running", data["subscription_units"][0]["status"])
        self.assertEqual(
            {"pickup_location_name": None, "has_banking_data": True},
            data["prerequisites"],
        )
        self.assertEqual(MemberPaymentRhythm.Rhythm.MONTHLY, data["payment_rhythm"])

    def test_get_unknownMember_returns404(self):
        self._login_as_admin()

        response = self._get(member_id="unknown")

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
