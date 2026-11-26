from django.urls import reverse
from rest_framework import status

from tapir.bakery.models import AvailableBreadsForDeliveryDay
from tapir.bakery.services.copy_week_validator import CopyWeekValidator
from tapir.bakery.tests.factories import (
    AvailableBreadsForDeliveryDayFactory,
    BreadFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

# Far enough ahead that no day of these weeks is over.
FUTURE_YEAR = 2099
DAY = 3


class TestCopyWeekSettingsView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:copy-week-settings")
        self.client.force_login(MemberFactory.create(is_superuser=True))
        self.bread = BreadFactory.create(name="Roggen")
        AvailableBreadsForDeliveryDayFactory.create(
            year=FUTURE_YEAR, delivery_week=1, delivery_day=DAY, bread=self.bread
        )

    def _post(self, **overrides):
        data = {
            "source_year": FUTURE_YEAR,
            "source_week": 1,
            "target_year": FUTURE_YEAR,
            "target_week": 2,
            **overrides,
        }
        return self.client.post(self.url, data, content_type="application/json")

    def test_get_default_listsTheEarlierWeeks(self):
        response = self.client.get(self.url, {"year": FUTURE_YEAR, "delivery_week": 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["sources"],
            [{"year": FUTURE_YEAR, "delivery_week": 1, "bread_count": 1}],
        )

    def test_post_default_copiesTheWeek(self):
        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"copied_days": [DAY], "kept_days": [], "cleared_choices": 0},
        )
        self.assertTrue(
            AvailableBreadsForDeliveryDay.objects.filter(
                year=FUTURE_YEAR, delivery_week=2, bread=self.bread
            ).exists()
        )

    def test_post_dryRun_changesNothing(self):
        response = self._post(dry_run=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["copied_days"], [DAY])
        self.assertFalse(
            AvailableBreadsForDeliveryDay.objects.filter(
                year=FUTURE_YEAR, delivery_week=2
            ).exists()
        )

    def test_post_sourceNotBeforeTarget_returns400(self):
        for source_week in (2, 3):
            with self.subTest(source_week=source_week):
                response = self._post(source_week=source_week)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    response.data["error"],
                    CopyWeekValidator.SOURCE_NOT_BEFORE_TARGET,
                )

    def test_post_weekNotInTheYear_returns400(self):
        # 2027 has 52 ISO weeks.
        response = self._post(
            source_year=2027, source_week=52, target_year=2027, target_week=53
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self.client.get(self.url, {"year": FUTURE_YEAR, "delivery_week": 2})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
