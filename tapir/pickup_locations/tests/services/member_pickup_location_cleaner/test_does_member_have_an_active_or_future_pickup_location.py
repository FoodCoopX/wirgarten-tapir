import datetime
from unittest.mock import patch, Mock

from tapir.pickup_locations.services.member_pickup_location_cleaner import (
    MemberPickupLocationCleaner,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.tests.factories import MemberFactory, MemberPickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestDoesMemberHaveAnActiveOrFuturePickupLocation(TapirUnitTest):
    @patch.object(
        MemberPickupLocationGetter,
        "get_member_pickup_locations_objects_by_member_id",
        autospec=True,
    )
    def test_doesMemberHaveAnActiveOrFuturePickupLocation_memberHasNoLocationObject_returnsFalse(
        self, mock_get_member_pickup_locations_objects_by_member_id: Mock
    ):
        mock_get_member_pickup_locations_objects_by_member_id.return_value = {}

        member = Mock()
        reference_date = Mock()
        cache = Mock()

        result = MemberPickupLocationCleaner._does_member_have_an_active_or_future_pickup_location(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)

        mock_get_member_pickup_locations_objects_by_member_id.assert_called_once_with(
            cache=cache
        )

    @patch.object(
        MemberPickupLocationGetter,
        "get_member_pickup_locations_objects_by_member_id",
        autospec=True,
    )
    def test_doesMemberHaveAnActiveOrFuturePickupLocation_memberHasAFutureLocationObject_returnsTrue(
        self, mock_get_member_pickup_locations_objects_by_member_id: Mock
    ):
        member = MemberFactory.build()
        reference_date = datetime.date(year=2028, month=6, day=15)

        mock_get_member_pickup_locations_objects_by_member_id.return_value = {
            member.id: [
                MemberPickupLocationFactory.build(
                    valid_from=reference_date + datetime.timedelta(days=3)
                ),
                MemberPickupLocationFactory.build(
                    valid_from=reference_date - datetime.timedelta(days=3)
                ),
            ]
        }

        cache = Mock()

        result = MemberPickupLocationCleaner._does_member_have_an_active_or_future_pickup_location(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertTrue(result)

        mock_get_member_pickup_locations_objects_by_member_id.assert_called_once_with(
            cache=cache
        )

    @patch.object(
        MemberPickupLocationGetter,
        "get_member_pickup_locations_objects_by_member_id",
        autospec=True,
    )
    def test_doesMemberHaveAnActiveOrFuturePickupLocation_onlyPastLocationsAndMostRecentLocationIsNone_returnsFalse(
        self, mock_get_member_pickup_locations_objects_by_member_id: Mock
    ):
        member = MemberFactory.build()
        reference_date = datetime.date(year=2028, month=6, day=15)

        mock_get_member_pickup_locations_objects_by_member_id.return_value = {
            member.id: [
                MemberPickupLocationFactory.build(
                    valid_from=reference_date - datetime.timedelta(days=3),
                    pickup_location=None,
                ),
                MemberPickupLocationFactory.build(
                    valid_from=reference_date - datetime.timedelta(days=10)
                ),
            ]
        }

        cache = Mock()

        result = MemberPickupLocationCleaner._does_member_have_an_active_or_future_pickup_location(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)

        mock_get_member_pickup_locations_objects_by_member_id.assert_called_once_with(
            cache=cache
        )

    @patch.object(
        MemberPickupLocationGetter,
        "get_member_pickup_locations_objects_by_member_id",
        autospec=True,
    )
    def test_doesMemberHaveAnActiveOrFuturePickupLocation_onlyPastLocationsAndMostRecentLocationIsNotNone_returnsTrue(
        self, mock_get_member_pickup_locations_objects_by_member_id: Mock
    ):
        member = MemberFactory.build()
        reference_date = datetime.date(year=2028, month=6, day=15)

        mock_get_member_pickup_locations_objects_by_member_id.return_value = {
            member.id: [
                MemberPickupLocationFactory.build(
                    valid_from=reference_date - datetime.timedelta(days=3)
                ),
                MemberPickupLocationFactory.build(
                    valid_from=reference_date - datetime.timedelta(days=10),
                    pickup_location=None,
                ),
            ]
        }

        cache = Mock()

        result = MemberPickupLocationCleaner._does_member_have_an_active_or_future_pickup_location(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertTrue(result)

        mock_get_member_pickup_locations_objects_by_member_id.assert_called_once_with(
            cache=cache
        )
