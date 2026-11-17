import datetime

from tapir.generic_exports.services.payment_column_provider import PaymentColumnProvider
from tapir.generic_exports.services.payment_segment_provider import (
    PaymentSegmentProvider,
)
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PaymentFactory, PaymentTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentSegmentProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=True
        )

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
        self.assertEqual(
            PaymentSegmentProvider.get_description_all_payments_this_month,
            segment.get_description,
        )

    def test_getDescriptionAllPaymentsThisMonth_featureEnabled_mentionsExclusions(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED,
            value=True,
        )

        result = PaymentSegmentProvider.get_description_all_payments_this_month(
            cache=cache
        )

        self.assertIn("vom Zahlungsexport ausgeschlossen", result)

    def test_getDescriptionAllPaymentsThisMonth_featureDisabled_returnsBaseDescription(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED,
            value=False,
        )

        result = PaymentSegmentProvider.get_description_all_payments_this_month(
            cache=cache
        )

        self.assertEqual(
            PaymentSegmentProvider.DESCRIPTION_ALL_PAYMENTS_THIS_MONTH, result
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

    def test_getQuerysetAllPaymentsThisMonth_memberExcludedAtDueDate_paymentNotIncluded(
        self,
    ):
        excluded = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=15), transaction=None
        )
        PaymentExportExclusionPeriodFactory.create(
            member=excluded.mandate_ref.member,
            start_date=datetime.date(year=1997, month=7, day=15),
            end_date=datetime.date(year=1997, month=7, day=15),
        )
        included = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=15)
        )

        result = PaymentSegmentProvider.get_queryset_all_payments_this_month(
            reference_datetime=datetime.datetime(year=1997, month=7, day=15)
        )

        self.assertEqual([included], list(result))

    def test_getQuerysetAllPaymentsThisMonth_periodWithoutEndDate_paymentNotIncluded(
        self,
    ):
        excluded = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=15), transaction=None
        )
        PaymentExportExclusionPeriodFactory.create(
            member=excluded.mandate_ref.member,
            start_date=datetime.date(year=1990, month=1, day=1),
            end_date=None,
        )

        result = PaymentSegmentProvider.get_queryset_all_payments_this_month(
            reference_datetime=datetime.datetime(year=1997, month=7, day=15)
        )

        self.assertEqual(0, result.count())

    def test_getQuerysetAllPaymentsThisMonth_featureDisabled_paymentIncluded(self):
        self._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=False
        )
        payment = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=15)
        )
        PaymentExportExclusionPeriodFactory.create(
            member=payment.mandate_ref.member,
            start_date=datetime.date(year=1990, month=1, day=1),
            end_date=None,
        )

        result = PaymentSegmentProvider.get_queryset_all_payments_this_month(
            reference_datetime=datetime.datetime(year=1997, month=7, day=15)
        )

        self.assertEqual([payment], list(result))

    def test_getQuerysetAllPaymentsThisMonth_coopSharePaymentOfExcludedMember_paymentIncluded(
        self,
    ):
        payment = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=15),
            type=PAYMENT_TYPE_COOP_SHARES,
        )
        PaymentExportExclusionPeriodFactory.create(
            member=payment.mandate_ref.member,
            start_date=datetime.date(year=1990, month=1, day=1),
            end_date=None,
        )

        result = PaymentSegmentProvider.get_queryset_all_payments_this_month(
            reference_datetime=datetime.datetime(year=1997, month=7, day=15)
        )

        self.assertEqual([payment], list(result))

    def test_getQuerysetAllPaymentsThisMonth_dueDateOutsidePeriod_paymentIncluded(
        self,
    ):
        payment = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=15)
        )
        PaymentExportExclusionPeriodFactory.create(
            member=payment.mandate_ref.member,
            start_date=datetime.date(year=1997, month=7, day=16),
            end_date=None,
        )
        PaymentExportExclusionPeriodFactory.create(
            member=payment.mandate_ref.member,
            start_date=datetime.date(year=1997, month=1, day=1),
            end_date=datetime.date(year=1997, month=7, day=14),
        )

        result = PaymentSegmentProvider.get_queryset_all_payments_this_month(
            reference_datetime=datetime.datetime(year=1997, month=7, day=15)
        )

        self.assertEqual([payment], list(result))

    def test_getQuerysetAllPaymentsThisMonth_exportedPaymentFlaggedAsExcluded_paymentNotIncluded(
        self,
    ):
        PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=15),
            transaction=PaymentTransactionFactory.create(),
            excluded_from_export=True,
        )

        result = PaymentSegmentProvider.get_queryset_all_payments_this_month(
            reference_datetime=datetime.datetime(year=1997, month=7, day=15)
        )

        self.assertEqual(0, result.count())

    def test_getQuerysetAllPaymentsThisMonth_exportedPaymentNotFlaggedButMemberExcludedNow_paymentIncluded(
        self,
    ):
        payment = PaymentFactory.create(
            due_date=datetime.date(year=1997, month=7, day=15),
            transaction=PaymentTransactionFactory.create(),
            excluded_from_export=False,
        )
        PaymentExportExclusionPeriodFactory.create(
            member=payment.mandate_ref.member,
            start_date=datetime.date(year=1990, month=1, day=1),
            end_date=None,
        )

        result = PaymentSegmentProvider.get_queryset_all_payments_this_month(
            reference_datetime=datetime.datetime(year=1997, month=7, day=15)
        )

        self.assertEqual([payment], list(result))
