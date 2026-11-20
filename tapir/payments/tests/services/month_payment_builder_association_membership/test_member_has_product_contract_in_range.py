import datetime
from unittest.mock import patch, Mock

from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestMemberHasProductContractInRange(TapirUnitTest):
    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_subscriptionOverlapsRange_returnsTrue(self, mock_get_subscriptions: Mock):
        member = MemberFactory.build(id="member-id")
        cache = {}
        mock_get_subscriptions.return_value = [
            SubscriptionFactory.build(
                start_date=datetime.date(year=2026, month=1, day=1),
                end_date=datetime.date(year=2026, month=12, day=31),
            )
        ]

        result = MonthPaymentBuilderAssociationMembership.member_has_product_contract_in_range(
            member=member,
            range_start=datetime.date(year=2026, month=3, day=1),
            range_end=datetime.date(year=2026, month=3, day=31),
            cache=cache,
        )

        self.assertTrue(result)
        mock_get_subscriptions.assert_called_once_with(
            member_id="member-id", cache=cache
        )

    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_trialSubscriptionOverlapsRange_returnsTrue(
        self, mock_get_subscriptions: Mock
    ):
        member = MemberFactory.build(id="member-id")
        cache = {}
        mock_get_subscriptions.return_value = [
            SubscriptionFactory.build(
                start_date=datetime.date(year=2026, month=1, day=1),
                end_date=datetime.date(year=2026, month=12, day=31),
                trial_end_date_override=datetime.date(year=2026, month=3, day=15),
            )
        ]

        result = MonthPaymentBuilderAssociationMembership.member_has_product_contract_in_range(
            member=member,
            range_start=datetime.date(year=2026, month=3, day=1),
            range_end=datetime.date(year=2026, month=3, day=31),
            cache=cache,
        )

        self.assertTrue(result)

    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_subscriptionOutsideRange_returnsFalse(self, mock_get_subscriptions: Mock):
        member = MemberFactory.build(id="member-id")
        cache = {}
        mock_get_subscriptions.return_value = [
            SubscriptionFactory.build(
                start_date=datetime.date(year=2025, month=1, day=1),
                end_date=datetime.date(year=2025, month=12, day=31),
            )
        ]

        result = MonthPaymentBuilderAssociationMembership.member_has_product_contract_in_range(
            member=member,
            range_start=datetime.date(year=2026, month=3, day=1),
            range_end=datetime.date(year=2026, month=3, day=31),
            cache=cache,
        )

        self.assertFalse(result)

    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_noSubscriptions_returnsFalse(self, mock_get_subscriptions: Mock):
        member = MemberFactory.build(id="member-id")
        cache = {}
        mock_get_subscriptions.return_value = []

        result = MonthPaymentBuilderAssociationMembership.member_has_product_contract_in_range(
            member=member,
            range_start=datetime.date(year=2026, month=3, day=1),
            range_end=datetime.date(year=2026, month=3, day=31),
            cache=cache,
        )

        self.assertFalse(result)
