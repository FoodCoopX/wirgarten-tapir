import datetime
from decimal import Decimal
from unittest.mock import patch, Mock, call

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildPaymentsForSolidarityContributions(TapirIntegrationTest):
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

        payment_m1 = PaymentFactory.build()
        payment_m2 = PaymentFactory.build()
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

        payment_m1 = PaymentFactory.build()
        payment_m2 = PaymentFactory.build()
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

    def test_buildPaymentsForSolidarityContribution_mixedTrialAndNotTrialInRhythmPeriod_buildsCorrectPayments(
        self,
    ):
        # Regression test for #863

        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_ENABLED).update(
            value=True
        )
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_DURATION).update(
            value=8
        )  # The trial period of the soli contribution should end during february
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_START_DATE).update(
            value=datetime.date(year=2020, month=1, day=1)
        )
        member = MemberFactory.create()
        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2020, month=1, day=1),
            amount=Decimal("4.33"),
        )
        # We define a past contribution so that get_current_and_renewed_solidarity_contributions returns a non-empty array.
        # This makes sure that build_payment_for_contract_and_member gets called.
        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2019, month=1, day=1),
            amount=Decimal("4.33"),
        )
        MemberPaymentRhythm.objects.create(
            member=member,
            valid_from=datetime.date(year=2020, month=1, day=1),
            rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
        )
        GrowingPeriodFactory.create(start_date=datetime.date(year=2020, month=1, day=1))

        cache = {}
        generated_payments = set()

        payments_in_trial_february = MonthPaymentBuilderSolidarityContributions.build_payments_for_solidarity_contributions(
            current_month=datetime.date(year=2020, month=2, day=1),
            cache=cache,
            generated_payments=generated_payments,
            in_trial=True,
        )
        generated_payments.update(payments_in_trial_february)

        self.assertEqual(
            1,
            len(payments_in_trial_february),
            "There should be one payment for january generated in february, since the contribution is in trial all of january",
        )
        payment_in_trial_february = payments_in_trial_february[0]
        self.assertEqual(Decimal("4.33"), payment_in_trial_february.amount)
        self.assertEqual(
            datetime.date(year=2020, month=1, day=1),
            payment_in_trial_february.subscription_payment_range_start,
        )
        self.assertEqual(
            datetime.date(year=2020, month=1, day=31),
            payment_in_trial_february.subscription_payment_range_end,
        )

        payments_not_in_trial = MonthPaymentBuilderSolidarityContributions.build_payments_for_solidarity_contributions(
            current_month=datetime.date(year=2020, month=2, day=1),
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
        )
        generated_payments.update(payments_not_in_trial)

        self.assertEqual(
            0,
            len(payments_not_in_trial),
            "Since the contribution is still in trial for parts of february, no payment should be generated there yet",
        )

        payments_in_trial_march = MonthPaymentBuilderSolidarityContributions.build_payments_for_solidarity_contributions(
            current_month=datetime.date(year=2020, month=3, day=1),
            cache=cache,
            generated_payments=generated_payments,
            in_trial=True,
        )
        generated_payments.update(payments_in_trial_march)

        self.assertEqual(
            1,
            len(payments_in_trial_march),
            "There should be a payment for February generated in March since the contribution is still on trial for parts of February",
        )
        payment_in_trial_march = payments_in_trial_march[0]
        self.assertEqual(Decimal("4.33"), payment_in_trial_march.amount)
        self.assertEqual(
            datetime.date(year=2020, month=2, day=1),
            payment_in_trial_march.subscription_payment_range_start,
        )
        self.assertEqual(
            datetime.date(year=2020, month=2, day=29),
            payment_in_trial_march.subscription_payment_range_end,
        )

        payments_not_in_trial_march = MonthPaymentBuilderSolidarityContributions.build_payments_for_solidarity_contributions(
            current_month=datetime.date(year=2020, month=3, day=1),
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
        )

        self.assertEqual(
            1,
            len(payments_not_in_trial_march),
            "In March we generated the payment for the rest of the year since the member's payment rhythm is yearly",
        )
        payment_not_in_trial_march = payments_not_in_trial_march[0]
        self.assertEqual(
            Decimal("43.30"),
            payment_not_in_trial_march.amount,
            "The amount should be for 10 full months (12 months of the year minus 2 first month of trial)",
        )
        self.assertEqual(
            datetime.date(year=2020, month=3, day=1),
            payment_not_in_trial_march.subscription_payment_range_start,
        )
        self.assertEqual(
            datetime.date(year=2020, month=12, day=31),
            payment_not_in_trial_march.subscription_payment_range_end,
        )
