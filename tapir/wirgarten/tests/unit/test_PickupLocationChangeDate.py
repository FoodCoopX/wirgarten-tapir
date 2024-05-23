from datetime import datetime

from django.test import TestCase

from tapir.wirgarten.service.delivery import calculate_pickup_location_change_date


class PickupLocationChangeDateTestCase(TestCase):
    def parse_date(self, date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").date()

    def test_calculatePickupLocationChangeDate_againstValidationData_dataMatches(self):
        """
        Test that the pickup location change date is calculated correctly.
        """

        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        with open(
                "tapir/wirgarten/tests/unit/resources/pickup_location_change_date_validation.csv"
        ) as validation_data:
            validation_data = validation_data.read()

        for row in validation_data.split("\n"):
            cols = row.split(";")

            self.assertEqual(
                calculate_pickup_location_change_date(
                    self.parse_date(cols[0]),
                    self.parse_date(cols[1]),
                    weekdays.index(cols[2]),
                ),
                self.parse_date(cols[3]),
            )
