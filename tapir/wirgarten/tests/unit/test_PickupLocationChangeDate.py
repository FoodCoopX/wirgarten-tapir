import datetime

from django.test import TestCase

from tapir.wirgarten.service.delivery import calculate_pickup_location_change_date


class PickupLocationChangeDateTestCase(TestCase):
    def test_calculatePickupLocationChangeDate_default_returnsCorrectDay(
        self,
    ):
        self.assertEqual(
            datetime.date(year=2025, month=11, day=9),
            calculate_pickup_location_change_date(
                reference_date=datetime.date(year=2025, month=11, day=3),
                change_until_weekday=6,
            ),
        )

        self.assertEqual(
            datetime.date(year=2025, month=11, day=9),
            calculate_pickup_location_change_date(
                reference_date=datetime.date(year=2025, month=11, day=6),
                change_until_weekday=6,
            ),
        )

        self.assertEqual(
            datetime.date(year=2025, month=11, day=4),
            calculate_pickup_location_change_date(
                reference_date=datetime.date(year=2025, month=11, day=3),
                change_until_weekday=1,
            ),
        )
