from datetime import date

from django.test import TestCase

from tapir.wirgarten.service.delivery import get_next_delivery_date


class DeliveryDateTestCase(TestCase):
    def test_getNextDeliveryDate_mutlipleCases_returnsCorrectDate(self):
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
