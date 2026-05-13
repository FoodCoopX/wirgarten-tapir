from unittest.mock import patch, Mock

from tapir.pickup_locations.services.member_pickup_location_cleaner import (
    MemberPickupLocationCleaner,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestShouldCleanPickupLocation(TapirUnitTest):
    @patch.object(
        MemberPickupLocationCleaner,
        "_does_member_have_at_least_one_delivered_subscription",
        autospec=True,
    )
    @patch.object(
        MemberPickupLocationCleaner,
        "_does_member_have_an_active_or_future_pickup_location",
        autospec=True,
    )
    def test_shouldCleanPickupLocation_memberHasLocationAndNoSubscription_returnsTrue(
        self,
        mock_does_member_have_an_active_or_future_pickup_location: Mock,
        mock_does_member_have_at_least_one_delivered_subscription: Mock,
    ):
        mock_does_member_have_an_active_or_future_pickup_location.return_value = True
        mock_does_member_have_at_least_one_delivered_subscription.return_value = False

        member = Mock()
        reference_date = Mock()
        cache = Mock()

        result = MemberPickupLocationCleaner._should_clean_pickup_location(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertTrue(result)

        mock_does_member_have_an_active_or_future_pickup_location.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )
        mock_does_member_have_at_least_one_delivered_subscription.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )

    @patch.object(
        MemberPickupLocationCleaner,
        "_does_member_have_at_least_one_delivered_subscription",
        autospec=True,
    )
    @patch.object(
        MemberPickupLocationCleaner,
        "_does_member_have_an_active_or_future_pickup_location",
        autospec=True,
    )
    def test_shouldCleanPickupLocation_memberHasLocationButHasSubscription_returnsFalse(
        self,
        mock_does_member_have_an_active_or_future_pickup_location: Mock,
        mock_does_member_have_at_least_one_delivered_subscription: Mock,
    ):
        mock_does_member_have_an_active_or_future_pickup_location.return_value = True
        mock_does_member_have_at_least_one_delivered_subscription.return_value = True

        member = Mock()
        reference_date = Mock()
        cache = Mock()

        result = MemberPickupLocationCleaner._should_clean_pickup_location(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)

        mock_does_member_have_an_active_or_future_pickup_location.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )
        mock_does_member_have_at_least_one_delivered_subscription.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )

    @patch.object(
        MemberPickupLocationCleaner,
        "_does_member_have_at_least_one_delivered_subscription",
        autospec=True,
    )
    @patch.object(
        MemberPickupLocationCleaner,
        "_does_member_have_an_active_or_future_pickup_location",
        autospec=True,
    )
    def test_shouldCleanPickupLocation_memberHasNoLocation_returnsFalse(
        self,
        mock_does_member_have_an_active_or_future_pickup_location: Mock,
        mock_does_member_have_at_least_one_delivered_subscription: Mock,
    ):
        mock_does_member_have_an_active_or_future_pickup_location.return_value = False

        member = Mock()
        reference_date = Mock()
        cache = Mock()

        result = MemberPickupLocationCleaner._should_clean_pickup_location(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)

        mock_does_member_have_an_active_or_future_pickup_location.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )
        mock_does_member_have_at_least_one_delivered_subscription.assert_not_called()
