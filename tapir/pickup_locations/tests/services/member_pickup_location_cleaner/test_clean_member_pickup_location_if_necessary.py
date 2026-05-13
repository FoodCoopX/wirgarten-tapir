from unittest.mock import patch, Mock

from tapir.pickup_locations.services.member_pickup_location_cleaner import (
    MemberPickupLocationCleaner,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCleanMemberPickupLocationIfNecessary(TapirUnitTest):
    @patch.object(
        MemberPickupLocationSetter, "link_member_to_pickup_location", autospec=True
    )
    @patch.object(
        MemberPickupLocationCleaner, "_should_clean_pickup_location", autospec=True
    )
    def test_cleanMemberPickupLocationIfNecessary_shouldClean_cleans(
        self,
        mock_should_clean_pickup_location: Mock,
        mock_link_member_to_pickup_location: Mock,
    ):
        member = Mock()
        cache = Mock()
        reference_date = Mock()

        mock_should_clean_pickup_location.return_value = True

        MemberPickupLocationCleaner._clean_member_pickup_location_if_necessary(
            member=member, cache=cache, reference_date=reference_date, dry_run=False
        )

        mock_link_member_to_pickup_location.assert_called_once_with(
            pickup_location_id=None,
            member=member,
            cache=cache,
            actor=None,
            valid_from=reference_date,
        )
        mock_should_clean_pickup_location.assert_called_once_with(
            member=member, cache=cache, reference_date=reference_date
        )

    @patch.object(
        MemberPickupLocationSetter, "link_member_to_pickup_location", autospec=True
    )
    @patch.object(
        MemberPickupLocationCleaner, "_should_clean_pickup_location", autospec=True
    )
    def test_cleanMemberPickupLocationIfNecessary_shouldNotClean_doesntCleans(
        self,
        mock_should_clean_pickup_location: Mock,
        mock_link_member_to_pickup_location: Mock,
    ):
        member = Mock()
        cache = Mock()
        reference_date = Mock()

        mock_should_clean_pickup_location.return_value = False

        MemberPickupLocationCleaner._clean_member_pickup_location_if_necessary(
            member=member, cache=cache, reference_date=reference_date, dry_run=False
        )

        mock_link_member_to_pickup_location.assert_not_called()
        mock_should_clean_pickup_location.assert_called_once_with(
            member=member, cache=cache, reference_date=reference_date
        )

    @patch.object(
        MemberPickupLocationSetter, "link_member_to_pickup_location", autospec=True
    )
    @patch.object(
        MemberPickupLocationCleaner, "_should_clean_pickup_location", autospec=True
    )
    def test_cleanMemberPickupLocationIfNecessary_shouldCleanButDryRun_doesntCleans(
        self,
        mock_should_clean_pickup_location: Mock,
        mock_link_member_to_pickup_location: Mock,
    ):
        member = Mock()
        cache = Mock()
        reference_date = Mock()

        mock_should_clean_pickup_location.return_value = True

        MemberPickupLocationCleaner._clean_member_pickup_location_if_necessary(
            member=member, cache=cache, reference_date=reference_date, dry_run=True
        )

        mock_link_member_to_pickup_location.assert_not_called()
        mock_should_clean_pickup_location.assert_called_once_with(
            member=member, cache=cache, reference_date=reference_date
        )
