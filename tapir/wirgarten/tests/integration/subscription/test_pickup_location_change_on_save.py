import datetime

from tapir.pickup_locations.models import MemberPickupLocation
from tapir.wirgarten.forms.subscription import BaseProductForm, _as_date
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationChangeOnSave(TapirIntegrationTest):
    """
    Renewing a contract while changing pickup location.

    pickup_location_change_date is a ChoiceField, so its cleaned value is the
    string form of a date, while MemberPickupLocationSetter does date
    arithmetic with it - and a string has no .weekday().
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create()
        self.old_location = PickupLocationFactory.create(name="Hofladen")
        self.new_location = PickupLocationFactory.create(
            name="Marktstand", coords_lon=1
        )
        # A station with opening times is the case that exercises the date
        # arithmetic; with none it is skipped and a string would pass through.
        for location in (self.old_location, self.new_location):
            PickupLocationOpeningTime.objects.create(
                pickup_location=location,
                day_of_week=3,
                open_time=datetime.time(8),
                close_time=datetime.time(18),
            )

    def _form(self):
        # _change_pickup_location only reads self.actor and self.cache, so the
        # method can be exercised without building the whole form.
        form = BaseProductForm.__new__(BaseProductForm)
        form.actor = self.member
        form.cache = {}
        return form

    def test_changePickupLocation_dateAsStringFromTheChoiceField_isAccepted(self):
        change_date = datetime.date(2026, 9, 10)
        MemberPickupLocation.objects.create(
            member=self.member,
            pickup_location=self.old_location,
            valid_from=datetime.date(2026, 1, 1),
        )

        self._form()._change_pickup_location(
            self.member, self.new_location, str(change_date)
        )

        written = MemberPickupLocation.objects.get(
            member=self.member, pickup_location=self.new_location
        )
        self.assertEqual(written.valid_from, change_date)

    def test_changePickupLocation_memberWithoutAPreviousLocation_stillWorks(self):
        self._form()._change_pickup_location(
            self.member, self.new_location, str(datetime.date(2026, 9, 10))
        )

        self.assertTrue(
            MemberPickupLocation.objects.filter(
                member=self.member, pickup_location=self.new_location
            ).exists()
        )

    def test_asDate_passesRealDatesThroughUntouched(self):
        self.assertEqual(
            _as_date(datetime.date(2026, 9, 10)), datetime.date(2026, 9, 10)
        )
        self.assertIsNone(_as_date(None))
