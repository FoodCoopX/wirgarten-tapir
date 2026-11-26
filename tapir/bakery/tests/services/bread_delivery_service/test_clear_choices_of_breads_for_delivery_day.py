import datetime
from unittest.mock import patch

from django.test import override_settings

from tapir.bakery.models import BreadDelivery
from tapir.bakery.services.breaddelivery_service import BreadDeliveryService
from tapir.bakery.tests.factories import BreadDeliveryFactory, BreadFactory
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone

FROZEN_DATE = datetime.date(2026, 3, 14)  # Saturday, week 11
# The real lookup, taken before a test patches it.
GET_CHOICES_OF_BREADS_FOR_DELIVERY_DAY = (
    BreadDeliveryService.get_choices_of_breads_for_delivery_day
)


@override_settings(BAKERY_ENABLED=True)
class TestClearChoicesOfBreadsForDeliveryDay(TapirIntegrationTest):
    """FROZEN_DATE is the Saturday of week 11."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime.combine(FROZEN_DATE, datetime.time(12)))
        self.bread = BreadFactory.create(name="Roggenbrot")

    def _choice(self, week, day, **kwargs):
        return BreadDeliveryFactory.create(
            year=2026,
            delivery_week=week,
            pickup_location=create_pickup_location_with_opening_times(open_days=[day]),
            bread=self.bread,
            **kwargs,
        )

    def _clear(self, week, day):
        return BreadDeliveryService.clear_choices_of_breads_for_delivery_day(
            [self.bread.id], 2026, week, day, cache={}
        )

    def test_clearChoicesOfBreadsForDeliveryDay_laterDayOfTheWeek_clearsTheChoice(
        self,
    ):
        delivery = self._choice(week=11, day=6)

        self.assertEqual(self._clear(week=11, day=6), 1)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread_id)

    def test_clearChoicesOfBreadsForDeliveryDay_todayOrAnEarlierDay_keepsTheChoice(
        self,
    ):
        for day in (2, 5):
            with self.subTest(day=day):
                delivery = self._choice(week=11, day=day)

                self.assertEqual(self._clear(week=11, day=day), 0)
                delivery.refresh_from_db()
                self.assertEqual(delivery.bread_id, self.bread.id)

    def test_clearChoicesOfBreadsForDeliveryDay_jokeredSlot_clearsTheChoice(self):
        delivery = self._choice(week=12, day=2, joker_taken=True)

        self.assertEqual(self._clear(week=12, day=2), 1)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread_id)

    @patch.object(BreadDeliveryService, "get_choices_of_breads_for_delivery_day")
    def test_clearChoicesOfBreadsForDeliveryDay_memberSwitchedSinceTheRead_keepsTheNewChoice(
        self, mock_get_choices_of_breads_for_delivery_day
    ):
        delivery = self._choice(week=12, day=2)
        other_bread = BreadFactory.create(name="Dinkelbrot")

        def switch_after_reading(*args, **kwargs):
            choices = GET_CHOICES_OF_BREADS_FOR_DELIVERY_DAY(*args, **kwargs)
            BreadDelivery.objects.filter(pk=delivery.pk).update(bread=other_bread)
            return choices

        mock_get_choices_of_breads_for_delivery_day.side_effect = switch_after_reading

        cleared = self._clear(week=12, day=2)

        self.assertEqual(cleared, 0)
        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, other_bread.id)
