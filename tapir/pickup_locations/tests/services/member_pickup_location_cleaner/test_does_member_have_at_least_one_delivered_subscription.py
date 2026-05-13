from unittest.mock import patch, Mock

from tapir.pickup_locations.services.member_pickup_location_cleaner import (
    MemberPickupLocationCleaner,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import NO_DELIVERY, WEEKLY
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestDoesMemberHaveAtLeastOneDeliveredSubscription(TapirUnitTest):
    @patch.object(
        TapirCache, "get_active_and_future_subscriptions_by_member_id", autospec=True
    )
    def test_doesMemberHaveAtLeastOneDeliveredSubscription_memberHasNoSubscription_returnsFalse(
        self, mock_get_active_and_future_subscriptions_by_member_id: Mock
    ):
        member = MemberFactory.build()
        reference_date = Mock()
        cache = Mock()

        mock_get_active_and_future_subscriptions_by_member_id.return_value = {}

        result = MemberPickupLocationCleaner._does_member_have_at_least_one_delivered_subscription(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)

        mock_get_active_and_future_subscriptions_by_member_id.assert_called_once_with(
            cache=cache, reference_date=reference_date
        )

    @patch.object(
        TapirCache, "get_active_and_future_subscriptions_by_member_id", autospec=True
    )
    def test_doesMemberHaveAtLeastOneDeliveredSubscription_memberHasOnlySubscriptionWithoutDelivery_returnsFalse(
        self, mock_get_active_and_future_subscriptions_by_member_id: Mock
    ):
        member = MemberFactory.build()
        reference_date = Mock()
        cache = Mock()

        mock_get_active_and_future_subscriptions_by_member_id.return_value = {
            member.id: [
                SubscriptionFactory.build(product__type__delivery_cycle=NO_DELIVERY[0])
            ]
        }

        result = MemberPickupLocationCleaner._does_member_have_at_least_one_delivered_subscription(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)

        mock_get_active_and_future_subscriptions_by_member_id.assert_called_once_with(
            cache=cache, reference_date=reference_date
        )

    @patch.object(
        TapirCache, "get_active_and_future_subscriptions_by_member_id", autospec=True
    )
    def test_doesMemberHaveAtLeastOneDeliveredSubscription_memberHasSubscriptionWithDelivery_returnsTrue(
        self, mock_get_active_and_future_subscriptions_by_member_id: Mock
    ):
        member = MemberFactory.build()
        reference_date = Mock()
        cache = Mock()

        mock_get_active_and_future_subscriptions_by_member_id.return_value = {
            member.id: [
                SubscriptionFactory.build(product__type__delivery_cycle=NO_DELIVERY[0]),
                SubscriptionFactory.build(product__type__delivery_cycle=WEEKLY[0]),
                SubscriptionFactory.build(product__type__delivery_cycle=NO_DELIVERY[0]),
            ]
        }

        result = MemberPickupLocationCleaner._does_member_have_at_least_one_delivered_subscription(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertTrue(result)

        mock_get_active_and_future_subscriptions_by_member_id.assert_called_once_with(
            cache=cache, reference_date=reference_date
        )
