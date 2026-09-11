import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestConvertWeeksToDateForSubscriptionChangesApiView(TapirIntegrationTest):
    URL = reverse("subscriptions:convert_weeks_to_date_for_subscription_change")

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self.client.get(self.URL)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_weeksWithinGrowingPeriod_returnsCorrectDates(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2026, month=1, day=1)
        )

        url = f"{self.URL}?start_week=10&end_week=20&subscription_id={subscription.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(response_content["start_date"], "2026-03-02")
        self.assertEqual(response_content["end_date"], "2026-05-17")

    def test_get_startWeekOverlapsGrowingPeriodStart_returnsFirstDayOfGrowingPeriod(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2026, month=1, day=1)
        )

        url = f"{self.URL}?start_week=1&end_week=10&subscription_id={subscription.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(response_content["start_date"], "2026-01-01")

    def test_get_endWeekOverlapsGrowingPeriodEnd_returnsLastDayOfGrowingPeriod(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2026, month=1, day=1)
        )

        url = f"{self.URL}?start_week=10&end_week=53&subscription_id={subscription.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(response_content["end_date"], "2026-12-31")
