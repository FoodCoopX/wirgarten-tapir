import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory


class TestBuildPaymentsForSolidarityContributions(SimpleTestCase):
    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MonthPaymentBuilderUtils,
        "build_payment_for_contract_and_member",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderSolidarityContributions,
        "get_current_and_renewed_solidarity_contributions",
        autospec=True,
    )
    def test_buildPaymentsForSolidarityContribution_notInTrial_buildsAPaymentForEachContribution(
        self,
        mock_get_current_and_renewed_solidarity_contributions: Mock,
        mock_build_payment_for_contract_and_member: Mock,
        mock_get_member_payment_rhythm: Mock,
    ):
        members = MemberFactory.build_batch(size=3)
        member_1, member_2, member_3 = members
        member_1.pk = "test_id_1"
        member_2.pk = "test_id_2"
        member_3.pk = "test_id_3"

        contribution_m1 = SolidarityContributionFactory.build(
            member=member_1, start_date=datetime.date(year=2020, month=1, day=1)
        )
        contribution_m2_1 = SolidarityContributionFactory.build(
            member=member_2, start_date=datetime.date(year=2020, month=1, day=1)
        )
        contribution_m2_2 = SolidarityContributionFactory.build(
            member=member_2, start_date=datetime.date(year=2020, month=1, day=1)
        )
        contribution_m3 = SolidarityContributionFactory.build(
            member=member_3, start_date=datetime.date(year=2020, month=1, day=1)
        )
        contributions = {
            member_1: {contribution_m1},
            member_2: {contribution_m2_1, contribution_m2_2},
            member_3: {contribution_m3},
        }

        mock_get_current_and_renewed_solidarity_contributions.return_value = [
            contribution_m1,
            contribution_m2_1,
            contribution_m2_2,
            contribution_m3,
        ]

        rhythms = {
            member_1: MemberPaymentRhythm.Rhythm.MONTHLY,
            member_2: MemberPaymentRhythm.Rhythm.YEARLY,
            member_3: MemberPaymentRhythm.Rhythm.QUARTERLY,
        }
        mock_get_member_payment_rhythm.side_effect = (
            lambda member, reference_date, cache: rhythms[member]
        )

        payment_m1 = PaymentFactory.build(mandate_ref__ref="1")
        payment_m2 = PaymentFactory.build(mandate_ref__ref="2")
        payments = {member_1: payment_m1, member_2: payment_m2, member_3: None}

        mock_build_payment_for_contract_and_member.side_effect = (
            lambda **kwargs: payments[kwargs["member"]]
        )

        cache = Mock()
        generated_payments = Mock()
        current_month = datetime.date(year=2020, month=1, day=1)

        result = MonthPaymentBuilderSolidarityContributions.build_payments_for_solidarity_contributions(
            current_month=current_month,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
        )

        self.assertEqual({payment_m1, payment_m2}, set(result))

        mock_get_current_and_renewed_solidarity_contributions.assert_called_once_with(
            cache=cache, first_of_month=current_month, is_in_trial=False
        )
        self.assertEqual(3, mock_get_member_payment_rhythm.call_count)
        mock_get_member_payment_rhythm.assert_has_calls(
            [
                call(member=member, reference_date=current_month, cache=cache)
                for member in members
            ],
            any_order=True,
        )
        self.assertEqual(3, mock_build_payment_for_contract_and_member.call_count)
        mock_build_payment_for_contract_and_member.assert_has_calls(
            [
                call(
                    member=member,
                    first_of_month=current_month,
                    contracts=contributions[member],
                    rhythm=rhythms[member],
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=False,
                    payment_type=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
                    total_to_pay_function=MonthPaymentBuilderSolidarityContributions.get_total_to_pay,
                    allow_negative_amounts=True,
                )
                for member in members
            ],
            any_order=True,
        )

    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MonthPaymentBuilderUtils,
        "build_payment_for_contract_and_member",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderSolidarityContributions,
        "get_current_and_renewed_solidarity_contributions",
        autospec=True,
    )
    def test_buildPaymentsForSolidarityContribution_inTrial_buildsAPaymentForEachContribution(
        self,
        mock_get_current_and_renewed_solidarity_contributions: Mock,
        mock_build_payment_for_contract_and_member: Mock,
        mock_get_member_payment_rhythm: Mock,
    ):
        members = MemberFactory.build_batch(size=3)
        member_1, member_2, member_3 = members
        member_1.pk = "test_id_1"
        member_2.pk = "test_id_2"
        member_3.pk = "test_id_3"

        contribution_m1 = SolidarityContributionFactory.build(
            member=member_1, start_date=datetime.date(year=2020, month=1, day=1)
        )
        contribution_m2_1 = SolidarityContributionFactory.build(
            member=member_2, start_date=datetime.date(year=2020, month=1, day=1)
        )
        contribution_m2_2 = SolidarityContributionFactory.build(
            member=member_2, start_date=datetime.date(year=2020, month=1, day=1)
        )
        contribution_m3 = SolidarityContributionFactory.build(
            member=member_3, start_date=datetime.date(year=2020, month=1, day=1)
        )
        contributions = {
            member_1: {contribution_m1},
            member_2: {contribution_m2_1, contribution_m2_2},
            member_3: {contribution_m3},
        }

        mock_get_current_and_renewed_solidarity_contributions.return_value = [
            contribution_m1,
            contribution_m2_1,
            contribution_m2_2,
            contribution_m3,
        ]

        rhythms = {
            member_1: MemberPaymentRhythm.Rhythm.MONTHLY,
            member_2: MemberPaymentRhythm.Rhythm.YEARLY,
            member_3: MemberPaymentRhythm.Rhythm.QUARTERLY,
        }
        mock_get_member_payment_rhythm.side_effect = (
            lambda member, reference_date, cache: rhythms[member]
        )

        payment_m1 = PaymentFactory.build(mandate_ref__ref="1")
        payment_m2 = PaymentFactory.build(mandate_ref__ref="2")
        payments = {member_1: payment_m1, member_2: payment_m2, member_3: None}

        mock_build_payment_for_contract_and_member.side_effect = (
            lambda **kwargs: payments[kwargs["member"]]
        )

        cache = Mock()
        generated_payments = Mock()
        current_month = datetime.date(year=2020, month=2, day=1)
        first_of_previous_month = datetime.date(year=2020, month=1, day=1)

        result = MonthPaymentBuilderSolidarityContributions.build_payments_for_solidarity_contributions(
            current_month=current_month,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=True,
        )

        self.assertEqual({payment_m1, payment_m2}, set(result))

        mock_get_current_and_renewed_solidarity_contributions.assert_called_once_with(
            cache=cache, first_of_month=first_of_previous_month, is_in_trial=True
        )
        mock_get_member_payment_rhythm.assert_not_called()
        self.assertEqual(3, mock_build_payment_for_contract_and_member.call_count)
        mock_build_payment_for_contract_and_member.assert_has_calls(
            [
                call(
                    member=member,
                    first_of_month=first_of_previous_month,
                    contracts=contributions[member],
                    rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=True,
                    payment_type=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
                    total_to_pay_function=MonthPaymentBuilderSolidarityContributions.get_total_to_pay,
                    allow_negative_amounts=True,
                )
                for member in members
            ],
            any_order=True,
        )
