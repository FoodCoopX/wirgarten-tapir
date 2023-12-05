from datetime import date, datetime

from django.test import TestCase

from tapir.wirgarten.service.delivery import (
    calculate_pickup_location_change_date,
    get_next_delivery_date,
)


class TestPickupLocationChangeDate(TestCase):
    def test_calculate_pickup_location_change_date(self):
        """
        Test that the pickup location change date is calculated correctly.
        """

        def parse_date(date_str):
            return datetime.strptime(date_str, "%Y-%m-%d").date()

        with open(
            "tapir/wirgarten/tests/data/pickup_location_change_date_validation.csv", "r"
        ) as f:
            validation_data = f.read()

            weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for row in validation_data.split("\n"):
                cols = row.split(";")

                self.assertEqual(
                    calculate_pickup_location_change_date(
                        parse_date(cols[0]),
                        parse_date(cols[1]),
                        weekdays.index(cols[2]),
                    ),
                    parse_date(cols[3]),
                )


class TestDeliveryDate(TestCase):
    def test_calculate_next_delivery_date(self):
        # Test Case 1: reference_date is Monday (0), delivery_weekday is Friday (4)
        reference_date = date(2023, 1, 2)  # Monday
        delivery_weekday = 4  # Friday
        expected_date = date(2023, 1, 6)  # Should be the next Friday
        self.assertEqual(
            get_next_delivery_date(reference_date, delivery_weekday), expected_date
        )

        # Test Case 2: reference_date is Saturday (5), delivery_weekday is Wednesday (2)
        reference_date = date(2023, 1, 7)  # Saturday
        delivery_weekday = 2  # Wednesday
        expected_date = date(2023, 1, 11)  # Should be the next Wednesday
        self.assertEqual(
            get_next_delivery_date(reference_date, delivery_weekday), expected_date
        )

        # Test Case 3: reference_date is Wednesday (2), delivery_weekday is Wednesday (2)
        reference_date = date(2023, 1, 4)  # Wednesday
        delivery_weekday = 2
        expected_date = date(2023, 1, 4)
        self.assertEqual(
            get_next_delivery_date(reference_date, delivery_weekday), expected_date
        )
