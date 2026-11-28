import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestConvertWeekToDateForSubscriptionChangeApiView(TapirIntegrationTest):
    URL = reverse("subscriptions:convert_week_to_date_for_subscription_change")

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _get(self, week: int | str, boundary: str):
        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2026, month=1, day=1)
        )
        return self.client.get(
            self.URL,
            data={
                "subscription_id": subscription.id,
                "week": week,
                "boundary": boundary,
            },
        )

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self.client.get(self.URL)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_weekWithinGrowingPeriod_returnsMondayOrSunday(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        start_response = self._get(week=10, boundary="start")
        end_response = self._get(week=20, boundary="end")

        self.assertStatusCode(start_response, status.HTTP_200_OK)
        self.assertEqual({"date": "2026-03-02", "error": None}, start_response.json())
        self.assertStatusCode(end_response, status.HTTP_200_OK)
        self.assertEqual({"date": "2026-05-17", "error": None}, end_response.json())

    def test_get_mondayOfWeekBeforeGrowingPeriod_returnsError(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self._get(week=1, boundary="start")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {
                "date": None,
                "error": "Der Montag der KW 1 liegt nicht in der Vertragsperiode",
            },
            response.json(),
        )

    def test_get_weekNotInGrowingPeriod_returnsError(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self._get(week=60, boundary="start")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIsNone(response.json()["date"])

    def test_get_weekIsNotANumber_returns400(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self._get(week="abc", boundary="start")

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
