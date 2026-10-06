import datetime

from tapir.pickup_locations.models import MemberPickupLocation
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.forms.subscription import BaseProductForm
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationChangeOnSave(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create()
        self.old_location = create_pickup_location_with_opening_times([3])
        self.new_location = create_pickup_location_with_opening_times([3])

    def build_form(self):
        form = BaseProductForm.__new__(BaseProductForm)
        form.actor = self.member
        form.cache = {}
        return form

    def test_changePickupLocation_dateAsString_linksTheMemberFromThatDate(self):
        change_date = datetime.date(2026, 9, 10)
        MemberPickupLocation.objects.create(
            member=self.member,
            pickup_location=self.old_location,
            valid_from=datetime.date(2026, 1, 1),
        )

        self.build_form()._change_pickup_location(
            self.member, self.new_location, str(change_date)
        )

        written = MemberPickupLocation.objects.get(
            member=self.member, pickup_location=self.new_location
        )
        self.assertEqual(written.valid_from, change_date)

    def test_changePickupLocation_memberWithoutAPreviousLocation_linksTheMember(
        self,
    ):
        self.build_form()._change_pickup_location(
            self.member, self.new_location, str(datetime.date(2026, 9, 10))
        )

        self.assertTrue(
            MemberPickupLocation.objects.filter(
                member=self.member, pickup_location=self.new_location
            ).exists()
        )
