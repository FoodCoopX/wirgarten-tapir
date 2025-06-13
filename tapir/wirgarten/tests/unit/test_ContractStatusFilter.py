import datetime

from django.test import TestCase
from tapir_mail.service.shortcuts import make_timezone_aware

from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    GrowingPeriodFactory,
    MemberFactory,
)
from tapir.wirgarten.tests.test_utils import mock_timezone, set_bypass_keycloak
from tapir.wirgarten.views.member.list.member_list import ContractStatusFilter


class ContractStatusFilterTestCase(TestCase):
    def setUp(self):
        set_bypass_keycloak()
        mock_timezone(self, datetime.datetime(year=2023, month=6, day=15))

        current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        next_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1),
            end_date=datetime.date(year=2024, month=12, day=31),
        )

        self.member_with_renewed_contract = MemberFactory.create(
            first_name="member_with_renewed_contract"
        )
        SubscriptionFactory.create(
            member=self.member_with_renewed_contract, period=current_growing_period
        )
        SubscriptionFactory.create(
            member=self.member_with_renewed_contract, period=next_growing_period
        )

        self.member_without_renewed_contract = MemberFactory.create(
            first_name="member_without_renewed_contract"
        )
        SubscriptionFactory.create(
            member=self.member_without_renewed_contract, period=current_growing_period
        )

        self.member_that_cancelled_during_trial_period = MemberFactory.create(
            first_name="member_that_cancelled_during_trial_period"
        )
        SubscriptionFactory.create(
            member=self.member_that_cancelled_during_trial_period,
            period=current_growing_period,
            start_date=datetime.date(year=2023, month=6, day=1),
            end_date=datetime.date(year=2023, month=7, day=1),
            cancellation_ts=make_timezone_aware(
                datetime.datetime(year=2023, month=6, day=10)
            ),
        )

        self.member_that_cancelled_after_trial_period = MemberFactory.create(
            first_name="member_that_cancelled_after_trial_period"
        )
        SubscriptionFactory.create(
            member=self.member_that_cancelled_after_trial_period,
            period=current_growing_period,
            cancellation_ts=make_timezone_aware(
                datetime.datetime(year=2023, month=4, day=15)
            ),
        )

        self.member_in_trial = MemberFactory.create(first_name="member_in_trial")
        SubscriptionFactory.create(
            member=self.member_in_trial,
            period=current_growing_period,
            start_date=datetime.date(year=2023, month=6, day=1),
        )

    def test_contractRenewed_default_returnsOnlyMembersWithRenewedContract(self):
        expected_in = [self.member_with_renewed_contract]
        self.check_results(expected_in, "Contract Renewed")

    def test_contractCancelled_default_returnsOnlyMembersWithCancelledContract(self):
        expected_in = [self.member_that_cancelled_after_trial_period]
        self.check_results(expected_in, "Contract Cancelled")

    def test_undecided_default_returnsOnlyUndecidedMembers(self):
        expected_in = [self.member_without_renewed_contract]
        self.check_results(expected_in, "Undecided")

    def check_results(self, expected_in, filter_type):
        contract_status_filter = ContractStatusFilter()
        result_queryset = contract_status_filter.filter(
            Member.objects.all(), filter_type
        )
        for member in Member.objects.all():
            assert_function = (
                self.assertIn if member in expected_in else self.assertNotIn
            )
            assert_function(member, result_queryset)
