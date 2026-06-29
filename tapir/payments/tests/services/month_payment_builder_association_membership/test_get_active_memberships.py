import datetime
from unittest.mock import patch, Mock, call

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetActiveMemberships(TapirUnitTest):
    maxDiff = 2000

    def setUp(self) -> None:
        self.membership_current_period_1 = AssociationMembershipFactory.build(
            start_date=datetime.date(year=2012, month=1, day=1), end_date=None
        )
        self.membership_current_period_2 = AssociationMembershipFactory.build(
            start_date=datetime.date(year=2012, month=1, day=1),
            end_date=datetime.date(year=2012, month=3, day=18),
        )
        self.membership_future_period = AssociationMembershipFactory.build(
            start_date=datetime.date(year=2013, month=1, day=1),
            end_date=datetime.date(year=2013, month=12, day=31),
        )
        self.membership_far_future = AssociationMembershipFactory.build(
            start_date=datetime.date(year=2014, month=1, day=1),
            end_date=datetime.date(year=2014, month=12, day=31),
        )
        self.membership_past_period = AssociationMembershipFactory.build(
            start_date=datetime.date(year=2011, month=1, day=1),
            end_date=datetime.date(year=2011, month=12, day=31),
        )

    def setup_mock(self, mock_get_all_association_memberships: Mock):
        mock_get_all_association_memberships.return_value = {
            self.membership_current_period_1,
            self.membership_current_period_2,
            self.membership_future_period,
            self.membership_far_future,
            self.membership_past_period,
        }

    @patch.object(TapirCache, "get_all_association_memberships", autospec=True)
    @patch.object(TapirCache, "get_growing_period_at_date", autospec=True)
    def test_getActiveMemberships_noCurrentGrowingPeriod_returnsEmptyList(
        self,
        mock_get_growing_period_at_date: Mock,
        mock_get_all_association_memberships: Mock,
    ):
        mock_get_growing_period_at_date.return_value = None
        self.setup_mock(mock_get_all_association_memberships)

        cache = Mock()

        result = MonthPaymentBuilderAssociationMembership.get_active_memberships(
            cache=cache, first_of_month=datetime.date(year=2012, month=2, day=1)
        )

        self.assertEqual([], result)

        mock_get_growing_period_at_date.assert_called_once_with(
            reference_date=datetime.date(year=2012, month=2, day=1), cache=cache
        )
        mock_get_all_association_memberships.assert_called_once_with(cache=cache)

    @patch.object(TapirCache, "get_all_association_memberships", autospec=True)
    @patch.object(TapirCache, "get_growing_period_at_date", autospec=True)
    def test_getActiveMemberships_hasCurrentPeriodButNoFuturePeriod_returnsMembershipsInCurrentPeriodOnly(
        self,
        mock_get_growing_period_at_date: Mock,
        mock_get_all_association_memberships: Mock,
    ):
        self.setup_mock(mock_get_all_association_memberships)

        growing_periods = {
            2012: GrowingPeriodFactory.build(
                start_date=datetime.date(year=2012, month=1, day=1)
            )
        }
        mock_get_growing_period_at_date.side_effect = (
            lambda reference_date, **kwargs: growing_periods.get(
                reference_date.year, None
            )
        )

        cache = Mock()

        result = MonthPaymentBuilderAssociationMembership.get_active_memberships(
            cache=cache, first_of_month=datetime.date(year=2012, month=2, day=1)
        )

        self.assertEqual(
            {self.membership_current_period_1, self.membership_current_period_2},
            set(result),
        )

        self.assertEqual(2, mock_get_growing_period_at_date.call_count)
        mock_get_growing_period_at_date.assert_has_calls(
            [
                call(
                    reference_date=datetime.date(year=2012, month=2, day=1), cache=cache
                ),
                call(
                    reference_date=datetime.date(year=2013, month=1, day=1), cache=cache
                ),
            ]
        )
        mock_get_all_association_memberships.assert_called_once_with(cache=cache)

    @patch.object(TapirCache, "get_all_association_memberships", autospec=True)
    @patch.object(TapirCache, "get_growing_period_at_date", autospec=True)
    def test_getActiveMemberships_hasCurrentPeriodAndFuturePeriod_returnsMembershipsInCurrentOrFuturePeriod(
        self,
        mock_get_growing_period_at_date: Mock,
        mock_get_all_association_memberships: Mock,
    ):
        self.setup_mock(mock_get_all_association_memberships)

        growing_periods = {
            2012: GrowingPeriodFactory.build(
                start_date=datetime.date(year=2012, month=1, day=1)
            ),
            2013: GrowingPeriodFactory.build(
                start_date=datetime.date(year=2013, month=1, day=1)
            ),
        }
        mock_get_growing_period_at_date.side_effect = (
            lambda reference_date, **kwargs: growing_periods.get(
                reference_date.year, None
            )
        )

        cache = Mock()

        result = MonthPaymentBuilderAssociationMembership.get_active_memberships(
            cache=cache, first_of_month=datetime.date(year=2012, month=2, day=1)
        )

        self.assertEqual(
            {
                self.membership_current_period_1,
                self.membership_current_period_2,
                self.membership_future_period,
            },
            set(result),
        )

        self.assertEqual(2, mock_get_growing_period_at_date.call_count)
        mock_get_growing_period_at_date.assert_has_calls(
            [
                call(
                    reference_date=datetime.date(year=2012, month=2, day=1), cache=cache
                ),
                call(
                    reference_date=datetime.date(year=2013, month=1, day=1), cache=cache
                ),
            ]
        )
        mock_get_all_association_memberships.assert_called_once_with(cache=cache)
