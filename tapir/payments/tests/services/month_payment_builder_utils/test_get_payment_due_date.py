import datetime
from unittest.mock import Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestMonthPaymentBuilderUtilsGetPaymentDueDate(TapirUnitTest):
    def test_getPaymentDueDate_contractsOnTrialAllCreatedAfterDueDate_returnsDueDateOneMonthAfterInputDate(
        self,
    ):
        cache = {}
        mock_parameter_value(cache=cache, key=ParameterKeys.PAYMENT_DUE_DAY, value=5)

        contract = Mock()
        contract.created_at = datetime.datetime(year=2025, month=4, day=12)

        result = MonthPaymentBuilderUtils.get_payment_due_date(
            first_of_month=datetime.date(year=2025, month=4, day=1),
            in_trial=True,
            contracts={contract},
            cache=cache,
        )

        # For this case and for test_getPaymentDueDate_contractsOnTrialAllCreatedBeforeDueDate_returnsDueDateOneMonthAfterNormalDate,
        # the result is the same: the payment is pushed one month anyway since we're on trial
        self.assertEqual(datetime.date(year=2025, month=5, day=5), result)

    def test_getPaymentDueDate_contractsOnTrialAllCreatedBeforeDueDate_returnsDueDateOneMonthAfterInputDate(
        self,
    ):
        cache = {}
        mock_parameter_value(cache=cache, key=ParameterKeys.PAYMENT_DUE_DAY, value=5)

        contract = Mock()
        contract.created_at = datetime.datetime(year=2025, month=4, day=3)

        result = MonthPaymentBuilderUtils.get_payment_due_date(
            first_of_month=datetime.date(year=2025, month=4, day=1),
            in_trial=True,
            contracts={contract},
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2025, month=5, day=5), result)

    def test_getPaymentDueDate_contractsNotOnTrialWithAtLeastOneCreatedBeforeDueDate_returnsDueDateOnInputMonth(
        self,
    ):
        cache = {}
        mock_parameter_value(cache=cache, key=ParameterKeys.PAYMENT_DUE_DAY, value=5)

        contract_1 = Mock()
        contract_1.start_date = datetime.date(year=2025, month=4, day=3)
        contract_1.created_at = None

        contract_2 = Mock()
        contract_2.created_at = datetime.datetime(year=2025, month=4, day=12)

        result = MonthPaymentBuilderUtils.get_payment_due_date(
            first_of_month=datetime.date(year=2025, month=4, day=1),
            in_trial=False,
            contracts={contract_1, contract_2},
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2025, month=4, day=5), result)

    def test_getPaymentDueDate_contractsNotOnTrialWithAllCreatedAfterDueDate_returnsDueDateOneMonthAfterInputDate(
        self,
    ):
        cache = {}
        mock_parameter_value(cache=cache, key=ParameterKeys.PAYMENT_DUE_DAY, value=5)

        contract_1 = Mock()
        contract_1.start_date = datetime.date(year=2025, month=4, day=15)
        contract_1.created_at = None

        contract_2 = Mock()
        contract_2.created_at = datetime.datetime(year=2025, month=4, day=12)

        result = MonthPaymentBuilderUtils.get_payment_due_date(
            first_of_month=datetime.date(year=2025, month=4, day=1),
            in_trial=False,
            contracts={contract_1, contract_2},
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2025, month=5, day=5), result)
