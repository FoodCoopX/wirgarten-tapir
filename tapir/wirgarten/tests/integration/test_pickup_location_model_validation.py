import datetime

from django.core.exceptions import ValidationError

from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationDateValidation(TapirIntegrationTest):
    def test_clean_startDateNotOnMonday_raisesValidationError(self):
        pickup_location = PickupLocationFactory.build(
            start_date=datetime.date(2026, 1, 6)
        )

        with self.assertRaises(ValidationError):
            pickup_location.clean()

    def test_clean_startDateNoneOrOnMonday_isValid(self):
        pickup_location = PickupLocationFactory.build(start_date=None)
        pickup_location.clean()

        pickup_location = PickupLocationFactory.build(
            start_date=datetime.date(2026, 1, 5)
        )
        pickup_location.clean()

    def test_save_startDateNotOnMonday_raisesValidationError(self):
        pickup_location = PickupLocationFactory.build(
            start_date=datetime.date(2026, 1, 6)
        )

        with self.assertRaises(ValidationError):
            pickup_location.save()

    def test_save_startDateNoneOrOnMonday_isValid(self):
        pickup_location = PickupLocationFactory.create(start_date=None)
        self.assertIsNotNone(pickup_location.id)

        pickup_location = PickupLocationFactory.create(
            start_date=datetime.date(2026, 1, 5)
        )
        self.assertIsNotNone(pickup_location.id)

    def test_clean_endDateNotOnSunday_raisesValidationError(self):
        pickup_location = PickupLocationFactory.build(
            end_date=datetime.date(2026, 12, 26)
        )

        with self.assertRaises(ValidationError):
            pickup_location.clean()

    def test_clean_endDateNoneOrOnSunday_isValid(self):
        pickup_location = PickupLocationFactory.build(end_date=None)
        pickup_location.clean()

        pickup_location = PickupLocationFactory.build(
            end_date=datetime.date(2026, 12, 27)
        )
        pickup_location.clean()

    def test_save_endDateNotOnSunday_raisesValidationError(self):
        pickup_location = PickupLocationFactory.build(
            end_date=datetime.date(2026, 12, 26)
        )

        with self.assertRaises(ValidationError):
            pickup_location.save()

    def test_save_endDateNoneOrOnSunday_isValid(self):
        pickup_location = PickupLocationFactory.create(end_date=None)
        self.assertIsNotNone(pickup_location.id)

        pickup_location = PickupLocationFactory.create(
            end_date=datetime.date(2026, 12, 27)
        )
        self.assertIsNotNone(pickup_location.id)
