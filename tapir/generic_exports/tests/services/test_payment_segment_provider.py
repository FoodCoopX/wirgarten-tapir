import datetime

from tapir.generic_exports.services.payment_column_provider import PaymentColumnProvider
from tapir.generic_exports.services.payment_segment_provider import (
    PaymentSegmentProvider,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentSegmentProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getPaymentSegments_default_returnsCorrectSegment(self):
        result = PaymentSegmentProvider.get_payment_segments()

        self.assertEqual(1, len(result))
        segment = result[0]
        self.assertEqual("payments.this_month", segment.id)
        self.assertEqual(
            PaymentSegmentProvider.get_queryset_all_payments_this_month,
            segment.get_queryset,
        )
        self.assertEqual(
            PaymentColumnProvider.get_payment_columns, segment.get_available_columns
        )

    def test_getQuerysetAllPaymentsThisMonth_default_includesOnlyPaymentsDueThisMonth(
        self,
    ):
        # should not be included:
        PaymentFactory.create(due_date=datetime.date(year=1997, month=6, day=18))
        PaymentFactory.create(due_date=datetime.date(year=1996, month=7, day=1))
        PaymentFactory.create(due_date=datetime.date(year=1997, month=8, day=3))

        # should be included:
        included_1 = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=1)
        )
        included_2 = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=31)
        )

        result = PaymentSegmentProvider.get_queryset_all_payments_this_month(
            reference_datetime=datetime.datetime(year=1997, month=7, day=15)
        )
        self.assertEqual(2, result.count())
        self.assertIn(included_1, result)
        self.assertIn(included_2, result)
