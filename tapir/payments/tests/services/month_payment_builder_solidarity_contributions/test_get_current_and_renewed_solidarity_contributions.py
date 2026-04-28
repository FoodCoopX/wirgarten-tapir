import datetime
from unittest.mock import patch, Mock, call

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.subscriptions.services.automatic_solidarity_contribution_renewal_service import (
    AutomaticSolidarityContributionRenewalService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache


class TestGetCurrentAndRenewedSolidarityContributions(TapirUnitTest):

    def setUp(self):
        # The contribution for january should be included even if it starts not on the 1st of the month, see #893 https://github.com/FoodCoopX/wirgarten-tapir/issues/893#issuecomment-3977453120
        start_date = datetime.date(year=1991, month=1, day=5)
        self.existing_contribution_in_trial = SolidarityContributionFactory.build(
            start_date=start_date
        )
        self.existing_contribution_in_trial_outside_of_given_date = (
            SolidarityContributionFactory.build(
                start_date=datetime.date(year=1990, month=1, day=1)
            )
        )
        self.existing_contribution_not_in_trial = SolidarityContributionFactory.build(
            start_date=start_date
        )
        self.existing_contribution_not_in_trial_outside_of_given_date = (
            SolidarityContributionFactory.build(
                start_date=datetime.date(year=1990, month=1, day=1)
            )
        )

        self.contribution_that_will_be_renewed_1 = Mock()
        self.contribution_that_will_be_renewed_2 = Mock()

        self.renewed_contribution_in_trial = SolidarityContributionFactory.build(
            start_date=start_date
        )
        self.renewed_contribution_not_in_trial = SolidarityContributionFactory.build(
            start_date=start_date
        )

    def prepare_mocks(
        self,
        mock_get_all_solidarity_contributions: Mock,
        mock_get_contributions_that_will_be_renewed: Mock,
        mock_build_renewed_contribution: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        mock_get_all_solidarity_contributions.return_value = {
            self.existing_contribution_in_trial,
            self.existing_contribution_not_in_trial,
            self.existing_contribution_in_trial_outside_of_given_date,
            self.existing_contribution_not_in_trial_outside_of_given_date,
        }
        mock_get_contributions_that_will_be_renewed.return_value = [
            self.contribution_that_will_be_renewed_1,
            self.contribution_that_will_be_renewed_2,
        ]
        mock_build_renewed_contribution.side_effect = lambda contribution, cache: (
            self.renewed_contribution_in_trial
            if contribution == self.contribution_that_will_be_renewed_1
            else self.renewed_contribution_not_in_trial
        )
        mock_is_contract_in_trial.side_effect = (
            lambda contract, reference_date, cache: contract
            in [self.existing_contribution_in_trial, self.renewed_contribution_in_trial]
        )

    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        AutomaticSolidarityContributionRenewalService,
        "build_renewed_contribution",
        autospec=True,
    )
    @patch.object(
        AutomaticSolidarityContributionRenewalService,
        "get_contributions_that_will_be_renewed",
        autospec=True,
    )
    @patch.object(TapirCache, "get_all_solidarity_contributions", autospec=True)
    def test_getCurrentAndRenewedSolidarityContributions_notInTrial_returnsContributionsNotInTrial(
        self,
        mock_get_all_solidarity_contributions: Mock,
        mock_get_contributions_that_will_be_renewed: Mock,
        mock_build_renewed_contribution: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        self.prepare_mocks(
            mock_get_all_solidarity_contributions,
            mock_get_contributions_that_will_be_renewed,
            mock_build_renewed_contribution,
            mock_is_contract_in_trial,
        )

        cache = Mock()
        first_of_month = datetime.date(year=1991, month=2, day=1)

        result = MonthPaymentBuilderSolidarityContributions.get_current_and_renewed_solidarity_contributions(
            cache=cache, first_of_month=first_of_month, is_in_trial=False
        )

        self.assertEqual(
            {
                self.renewed_contribution_not_in_trial,
                self.existing_contribution_not_in_trial,
            },
            set(result),
        )

        self.asset_mocks_called_correctly(
            mock_get_all_solidarity_contributions,
            mock_get_contributions_that_will_be_renewed,
            mock_build_renewed_contribution,
            mock_is_contract_in_trial,
            cache,
            first_of_month,
        )

    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        AutomaticSolidarityContributionRenewalService,
        "build_renewed_contribution",
        autospec=True,
    )
    @patch.object(
        AutomaticSolidarityContributionRenewalService,
        "get_contributions_that_will_be_renewed",
        autospec=True,
    )
    @patch.object(TapirCache, "get_all_solidarity_contributions", autospec=True)
    def test_getCurrentAndRenewedSolidarityContributions_inTrial_returnsContributionsInTrial(
        self,
        mock_get_all_solidarity_contributions: Mock,
        mock_get_contributions_that_will_be_renewed: Mock,
        mock_build_renewed_contribution: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        self.prepare_mocks(
            mock_get_all_solidarity_contributions,
            mock_get_contributions_that_will_be_renewed,
            mock_build_renewed_contribution,
            mock_is_contract_in_trial,
        )

        cache = Mock()
        first_of_month = datetime.date(year=1991, month=1, day=1)

        result = MonthPaymentBuilderSolidarityContributions.get_current_and_renewed_solidarity_contributions(
            cache=cache, first_of_month=first_of_month, is_in_trial=True
        )

        self.assertEqual(
            {
                self.renewed_contribution_in_trial,
                self.existing_contribution_in_trial,
            },
            set(result),
        )

        self.asset_mocks_called_correctly(
            mock_get_all_solidarity_contributions,
            mock_get_contributions_that_will_be_renewed,
            mock_build_renewed_contribution,
            mock_is_contract_in_trial,
            cache,
            first_of_month,
        )

    def asset_mocks_called_correctly(
        self,
        mock_get_all_solidarity_contributions: Mock,
        mock_get_contributions_that_will_be_renewed: Mock,
        mock_build_renewed_contribution: Mock,
        mock_is_contract_in_trial: Mock,
        cache,
        first_of_month,
    ):
        mock_get_all_solidarity_contributions.assert_called_once_with(cache=cache)
        mock_get_contributions_that_will_be_renewed.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        self.assertEqual(2, mock_build_renewed_contribution.call_count)
        mock_build_renewed_contribution.assert_has_calls(
            [
                call(contribution=contribution, cache=cache)
                for contribution in [
                    self.contribution_that_will_be_renewed_1,
                    self.contribution_that_will_be_renewed_2,
                ]
            ],
            any_order=True,
        )
        self.assertEqual(4, mock_is_contract_in_trial.call_count)
        mock_is_contract_in_trial.assert_has_calls(
            [
                call(contract=contribution, reference_date=first_of_month, cache=cache)
                for contribution in [
                    self.existing_contribution_in_trial,
                    self.existing_contribution_not_in_trial,
                    self.renewed_contribution_in_trial,
                    self.renewed_contribution_not_in_trial,
                ]
            ],
            any_order=True,
        )
