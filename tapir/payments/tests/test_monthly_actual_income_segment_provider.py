import datetime
from decimal import Decimal

from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.dataclasses import MonthlyActualIncome
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.monthly_actual_income_segment_provider import (
    MonthlyActualIncomeSegmentProvider,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PaymentFactory, PaymentTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMonthlyActualIncomeSegmentProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getListActualIncome_default_returnsCorrectData(self):
        due_date_this_month = datetime.date(year=2025, month=6, day=13)
        transaction_1 = PaymentTransactionFactory.create(
            month=due_date_this_month.replace(day=1)
        )
        PaymentFactory.create(
            type="Ernteanteil",
            amount=Decimal("10"),
            transaction=transaction_1,
            due_date=due_date_this_month,
        )
        PaymentFactory.create(
            type="Ernteanteil",
            amount=Decimal("15"),
            transaction=transaction_1,
            due_date=due_date_this_month,
        )
        PaymentFactory.create(
            type="Eieranteil",
            amount=Decimal("7.5"),
            transaction=transaction_1,
            due_date=due_date_this_month,
        )

        transaction_2 = PaymentTransactionFactory.create(
            month=due_date_this_month.replace(day=1)
        )
        PaymentFactory.create(
            type=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
            amount=Decimal("2.33"),
            transaction=transaction_2,
            due_date=due_date_this_month,
        )
        PaymentFactory.create(
            type=PAYMENT_TYPE_COOP_SHARES,
            amount=Decimal("50"),
            transaction=transaction_2,
            due_date=due_date_this_month,
        )

        # This one should not be included because it's in the future
        due_date_future = datetime.date(year=2025, month=7, day=13)
        transaction_3 = PaymentTransactionFactory.create(
            month=due_date_future.replace(day=1)
        )
        PaymentFactory.create(
            type="Ernteanteil",
            amount=Decimal("12.56"),
            transaction=transaction_3,
            due_date=due_date_future,
        )

        result = MonthlyActualIncomeSegmentProvider.get_list_actual_income(
            reference_datetime=datetime.datetime(year=2025, month=6, day=1, hour=8)
        )

        expected = [
            MonthlyActualIncome(source_name="Ernteanteil", income=Decimal("25")),
            MonthlyActualIncome(source_name="Eieranteil", income=Decimal("7.5")),
            MonthlyActualIncome(
                source_name=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
                income=Decimal("2.33"),
            ),
            MonthlyActualIncome(
                source_name=PAYMENT_TYPE_COOP_SHARES,
                income=Decimal("50"),
            ),
        ]
        self.assertEqual(len(expected), len(result))
        self.assertEqual(set(expected), set(result))
