import datetime

from django.core.exceptions import ValidationError

from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationStartDateValidation(TapirIntegrationTest):
    def test_clean_startDateNotOnFirstOfMonth_raisesValidationError(self):
        pickup_location = PickupLocationFactory.build(
            start_date=datetime.date(2026, 1, 15)
        )

        with self.assertRaises(ValidationError):
            pickup_location.clean()

    def test_clean_startDateNoneOrOnFirstOfMonth_isValid(self):
        pickup_location = PickupLocationFactory.build(start_date=None)
        pickup_location.clean()

        pickup_location = PickupLocationFactory.build(
            start_date=datetime.date(2026, 1, 1)
        )
        pickup_location.clean()

    def test_save_startDateNotOnFirstOfMonth_raisesValidationError(self):
        pickup_location = PickupLocationFactory.build(
            start_date=datetime.date(2026, 1, 15)
        )

        with self.assertRaises(ValidationError):
            pickup_location.save()

    def test_save_startDateNoneOrOnFirstOfMonth_isValid(self):
        pickup_location = PickupLocationFactory.create(start_date=None)
        self.assertIsNotNone(pickup_location.id)

        pickup_location = PickupLocationFactory.create(
            start_date=datetime.date(2026, 1, 1)
        )
        self.assertIsNotNone(pickup_location.id)

    def test_clean_endDateNotOnLastOfMonth_raisesValidationError(self):
        pickup_location = PickupLocationFactory.build(
            end_date=datetime.date(2026, 12, 15)
        )

        with self.assertRaises(ValidationError):
            pickup_location.clean()

    def test_clean_endDateNoneOrOnLastOfMonth_isValid(self):
        pickup_location = PickupLocationFactory.build(end_date=None)
        pickup_location.clean()

        pickup_location = PickupLocationFactory.build(
            end_date=datetime.date(2026, 12, 31)
        )
        pickup_location.clean()

    def test_save_endDateNotOnLastOfMonth_raisesValidationError(self):
        pickup_location = PickupLocationFactory.build(
            end_date=datetime.date(2026, 12, 15)
        )

        with self.assertRaises(ValidationError):
            pickup_location.save()

    def test_save_endDateNoneOrOnLastOfMonth_isValid(self):
        pickup_location = PickupLocationFactory.create(end_date=None)
        self.assertIsNotNone(pickup_location.id)

        pickup_location = PickupLocationFactory.create(
            end_date=datetime.date(2026, 12, 31)
        )
        self.assertIsNotNone(pickup_location.id)
