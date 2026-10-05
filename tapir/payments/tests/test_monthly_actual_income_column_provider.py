from decimal import Decimal

from tapir.payments.dataclasses import MonthlyActualIncome
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.payments.services.monthly_actual_income_column_provider import (
    MonthlyActualIncomeColumnProvider,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestMonthlyActualIncomeColumnProvider(TapirUnitTest):
    def test_getValueIncome_default_returnsFormatedPrice(self):
        input = MonthlyActualIncome(source_name="_", income=Decimal("13.37"))

        result = MonthlyActualIncomeColumnProvider.get_value_income(input, None, None)

        self.assertEqual("13,37", result)

    def test_getValueIncome_default_returnsSourceName(self):
        input = MonthlyActualIncome(source_name="test_name", income=Decimal("0"))

        result = MonthlyActualIncomeColumnProvider.get_value_source_name(
            input, None, None
        )

        self.assertEqual("test_name", result)

    def test_getValueIncome_sourceNameHasReplacement_returnsReplacement(self):
        input = MonthlyActualIncome(
            source_name=MonthPaymentBuilderAssociationMembership.PAYMENT_TYPE_ASSOCIATION_MEMBERSHIP,
            income=Decimal("0"),
        )

        result = MonthlyActualIncomeColumnProvider.get_value_source_name(
            input, None, None
        )

        self.assertEqual("Vereinsmitgliedschaften", result)
