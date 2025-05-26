import datetime

from django.urls import reverse

from tapir.deliveries.models import DeliveryDayAdjustment
from tapir.wirgarten.models import GrowingPeriod
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGrowingPeriodWithDeliveryDayAdjustmentsView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_get_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        growing_period = GrowingPeriodFactory.create()

        url = reverse("Deliveries:growing_period_with_adjustments")
        response = self.client.get(
            f"{url}?growing_period_id={growing_period.id}",
        )

        self.assertStatusCode(response, 403)

    def test_get_loggedInAsAdmin_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        growing_period = GrowingPeriodFactory.create()

        url = reverse("Deliveries:growing_period_with_adjustments")
        response = self.client.get(
            f"{url}?growing_period_id={growing_period.id}",
        )

        self.assertStatusCode(response, 200)

    def test_get_default_returnsCorrectData(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=3),
            end_date=datetime.date(year=2020, month=12, day=5),
            weeks_without_delivery=[12, 4, 7],
            max_jokers_per_member=3,
            joker_restrictions="15.02.-20.03.[3]",
        )

        DeliveryDayAdjustment.objects.create(
            growing_period=growing_period, calendar_week=6, adjusted_weekday=5
        )
        DeliveryDayAdjustment.objects.create(
            growing_period=growing_period, calendar_week=4, adjusted_weekday=1
        )

        url = reverse("Deliveries:growing_period_with_adjustments")
        response = self.client.get(
            f"{url}?growing_period_id={growing_period.id}",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(
            {
                "adjustments": [
                    {"adjusted_weekday": 1, "calendar_week": 4},
                    {"adjusted_weekday": 5, "calendar_week": 6},
                ],
                "growing_period_end_date": "2020-12-05",
                "growing_period_id": growing_period.id,
                "growing_period_start_date": "2020-01-03",
                "growing_period_weeks_without_delivery": [4, 7, 12],
                "joker_restrictions": "15.02.-20.03.[3]",
                "jokers_enabled": True,
                "max_jokers_per_member": 3,
            },
            response_content,
        )

    def test_patch_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        url = reverse("Deliveries:growing_period_with_adjustments")
        response = self.client.patch(url)

        self.assertStatusCode(response, 403)

    def test_patch_growingPeriodDoesntExist_returns404(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        url = reverse("Deliveries:growing_period_with_adjustments")
        response = self.client.patch(
            url,
            data={
                "growing_period_id": "invalid_id",
                "growing_period_start_date": "2020-01-03",
                "growing_period_end_date": "2020-12-05",
                "growing_period_weeks_without_delivery": [],
                "adjustments": [],
                "max_jokers_per_member": 2,
                "joker_restrictions": "disabled",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, 404)

    def test_patch_default_updatesGrowingPeriodAndAdjustments(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=3),
            end_date=datetime.date(year=2020, month=12, day=5),
            weeks_without_delivery=[12, 4, 7],
            max_jokers_per_member=2,
            joker_restrictions="15.02.-20.03.[3]",
        )
        DeliveryDayAdjustment.objects.create(
            growing_period=growing_period, calendar_week=6, adjusted_weekday=5
        )
        DeliveryDayAdjustment.objects.create(
            growing_period=growing_period, calendar_week=4, adjusted_weekday=1
        )

        url = reverse("Deliveries:growing_period_with_adjustments")
        response = self.client.patch(
            url,
            data={
                "growing_period_id": growing_period.id,
                "growing_period_start_date": "2021-01-04",
                "growing_period_end_date": "2021-05-06",
                "growing_period_weeks_without_delivery": [1, 2, 6],
                "adjustments": [
                    {"calendar_week": 7, "adjusted_weekday": 2},
                    {"calendar_week": 8, "adjusted_weekday": 3},
                    {"calendar_week": 9, "adjusted_weekday": 4},
                ],
                "max_jokers_per_member": 3,
                "joker_restrictions": "16.03.-21.04.[2]",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)

        self.assertEqual(1, GrowingPeriod.objects.count())
        growing_period.refresh_from_db()
        self.assertEqual(
            growing_period.start_date, datetime.date(year=2021, month=1, day=4)
        )
        self.assertEqual(
            growing_period.end_date, datetime.date(year=2021, month=5, day=6)
        )
        self.assertEqual(growing_period.weeks_without_delivery, [1, 2, 6])
        self.assertEqual(DeliveryDayAdjustment.objects.count(), 3)
        self.assertTrue(
            DeliveryDayAdjustment.objects.filter(
                calendar_week=7, adjusted_weekday=2, growing_period=growing_period
            ).exists()
        )
        self.assertTrue(
            DeliveryDayAdjustment.objects.filter(
                calendar_week=8, adjusted_weekday=3, growing_period=growing_period
            ).exists()
        )
        self.assertTrue(
            DeliveryDayAdjustment.objects.filter(
                calendar_week=9, adjusted_weekday=4, growing_period=growing_period
            ).exists()
        )
        self.assertEqual(3, growing_period.max_jokers_per_member)
        self.assertEqual("16.03.-21.04.[2]", growing_period.joker_restrictions)
