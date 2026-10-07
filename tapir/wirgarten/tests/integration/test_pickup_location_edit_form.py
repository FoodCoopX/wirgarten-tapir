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
        "start_date": "2026-01-05",
        "end_date": "2026-12-27",
    }
    data.update(overrides)
    return data


class TestPickupLocationEditForm(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_editForm_hasOptionalDateFields_returnsDatePickers(self):
        form = PickupLocationEditForm()
        for field_name in ("start_date", "end_date"):
            self.assertIn(field_name, form.fields)
            self.assertFalse(form.fields[field_name].required)
            self.assertEqual("date", form.fields[field_name].widget.input_type)

    def test_initial_forPickupLocationWithDates_populatedFromInstance(self):
        pickup_location = PickupLocationFactory.create(
            start_date=datetime.date(2026, 1, 5),
            end_date=datetime.date(2026, 12, 27),
        )

        form = PickupLocationEditForm(id=pickup_location.id)

        self.assertEqual(datetime.date(2026, 1, 5), form.fields["start_date"].initial)
        self.assertEqual(datetime.date(2026, 12, 27), form.fields["end_date"].initial)

    def test_save_withStartAndEndDate_persistsBothDates(self):
        pickup_location = PickupLocationFactory.create()

        form = PickupLocationEditForm(_valid_data(), id=pickup_location.id)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        pickup_location.refresh_from_db()
        self.assertEqual(datetime.date(2026, 1, 5), pickup_location.start_date)
        self.assertEqual(datetime.date(2026, 12, 27), pickup_location.end_date)

    def test_clean_endDateBeforeStartDate_addsError(self):
        form = PickupLocationEditForm(
            _valid_data(start_date="2026-12-07", end_date="2026-12-06")
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Ende darf nicht vor Beginn liegen.", form.errors.get("end_date", [])
        )

    def test_clean_startDateNotOnMonday_addsError(self):
        form = PickupLocationEditForm(_valid_data(start_date="2026-01-06"))

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Verteilstationen können nur an einem Montag geöffnet werden.",
            form.errors.get("start_date", []),
        )

    def test_clean_startDateOnMonday_isValid(self):
        form = PickupLocationEditForm(_valid_data(start_date="2026-01-05"))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(datetime.date(2026, 1, 5), form.cleaned_data.get("start_date"))

    def test_clean_rejectsEndDateNotOnSunday_reportsError(self):
        form = PickupLocationEditForm(_valid_data(end_date="2026-12-26"))

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Verteilstationen können nur an einem Sonntag geschlossen werden.",
            form.errors.get("end_date", []),
        )

    def test_clean_acceptsEndDateOnSunday_isValid(self):
        form = PickupLocationEditForm(_valid_data(end_date="2026-12-27"))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(datetime.date(2026, 12, 27), form.cleaned_data.get("end_date"))
