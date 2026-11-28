import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_subscription_change_member_data_builder import (
    AdminSubscriptionChangeMemberDataBuilder,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
@patch.object(TapirCache, "get_growing_period_at_date", autospec=True)
class TestAdminSubscriptionChangeMemberDataBuilderBuildSubscriptionUnits(TapirUnitTest):
    def setUp(self):
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2027, month=6, day=2))
        self.member = MemberFactory.build()
        self.previous_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        self.current_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

    def test_buildSubscriptionUnits_quantityThree_returnsOneUnitPerQuantity(
        self,
        mock_get_growing_period_at_date: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        mock_get_growing_period_at_date.return_value = self.current_period
        subscription = SubscriptionFactory.build(
            member=self.member, period=self.current_period, quantity=3
        )
        mock_get_all_subscriptions_for_member.return_value = [subscription]
        cache = {}

        units = AdminSubscriptionChangeMemberDataBuilder.build_subscription_units(
            member=self.member, cache=cache
        )

        self.assertEqual([1, 2, 3], [unit.unit_number for unit in units])
        self.assertEqual({subscription.id}, {unit.subscription_id for unit in units})
        self.assertEqual(
            {AdminSubscriptionChangeMemberDataBuilder.STATUS_RUNNING},
            {unit.status for unit in units},
        )
        mock_get_all_subscriptions_for_member.assert_called_once_with(
            member_id=self.member.id, cache=cache
        )

    def test_buildSubscriptionUnits_subscriptionEndedBeforeCurrentPeriod_isExcluded(
        self,
        mock_get_growing_period_at_date: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        mock_get_growing_period_at_date.return_value = self.current_period
        mock_get_all_subscriptions_for_member.return_value = [
            SubscriptionFactory.build(
                member=self.member, period=self.previous_period, quantity=1
            )
        ]

        units = AdminSubscriptionChangeMemberDataBuilder.build_subscription_units(
            member=self.member, cache={}
        )

        self.assertEqual([], units)

    def test_buildSubscriptionUnits_personalisedPrice_isMarkedAsPersonalised(
        self,
        mock_get_growing_period_at_date: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        mock_get_growing_period_at_date.return_value = self.current_period
        mock_get_all_subscriptions_for_member.return_value = [
            SubscriptionFactory.build(
                member=self.member,
                period=self.current_period,
                quantity=1,
                price_override=Decimal("25.00"),
            )
        ]

        units = AdminSubscriptionChangeMemberDataBuilder.build_subscription_units(
            member=self.member, cache={}
        )

        self.assertEqual(
            AdminSubscriptionChangeMemberDataBuilder.PRICE_PERSONALISED,
            units[0].price_category,
        )
