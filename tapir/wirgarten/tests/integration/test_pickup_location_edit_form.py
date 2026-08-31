import datetime

from tapir.wirgarten.forms.pickup_location import PickupLocationEditForm
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


def _valid_data(**overrides):
    data = {
        "coords": "11.5, 48.1",
        "name": "Test Abholort",
        "street": "Musterstraße 1",
        "postcode": "12345",
        "city": "Musterstadt",
        "monday_times": "08:00-09:00",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    data.update(overrides)
    return data


class TestPickupLocationEditForm(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_hasStartAndEndDateFields_optionalDatePickers(self):
        form = PickupLocationEditForm()
        for field_name in ("start_date", "end_date"):
            self.assertIn(field_name, form.fields)
            self.assertFalse(form.fields[field_name].required)
            self.assertEqual("date", form.fields[field_name].widget.input_type)

    def test_initial_populatedFromInstance(self):
        pickup_location = PickupLocationFactory.create(
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
        )

        form = PickupLocationEditForm(id=pickup_location.id)

        self.assertEqual(datetime.date(2026, 1, 1), form.fields["start_date"].initial)
        self.assertEqual(datetime.date(2026, 12, 31), form.fields["end_date"].initial)

    def test_save_persistsStartAndEndDate(self):
        pickup_location = PickupLocationFactory.create()

        form = PickupLocationEditForm(_valid_data(), id=pickup_location.id)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        pickup_location.refresh_from_db()
        self.assertEqual(datetime.date(2026, 1, 1), pickup_location.start_date)
        self.assertEqual(datetime.date(2026, 12, 31), pickup_location.end_date)

    def test_clean_rejectsEndDateBeforeStartDate(self):
        form = PickupLocationEditForm(
            _valid_data(start_date="2026-12-01", end_date="2026-01-01")
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Ende darf nicht vor Beginn liegen.", form.errors.get("end_date", [])
        )
