import datetime

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.solidarity_contribution.tests.factories import (
    SolidarityContributionFactory,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PaymentFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetIntendedUseCase(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()

        self.payment = PaymentFactory.create(
            subscription_payment_range_start=datetime.date(year=2025, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2025, month=1, day=31),
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=self.payment.mandate_ref.member,
            rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
            valid_from=self.payment.subscription_payment_range_start,
            actor=None,
            cache={},
        )
        self.growing_period = GrowingPeriodFactory.create(
            start_date=self.payment.subscription_payment_range_start
        )

    def test_getIntendedUseCase_rangeMismatchesNormalRhythm_returnsMultipleMonthInvoice(
        self,
    ):
        self.payment.subscription_payment_range_end = datetime.date(
            year=2026, month=2, day=15
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(
            ParameterKeys.PAYMENT_INTENDED_USE_MULTIPLE_MONTH_INVOICE, result
        )

    def test_getIntendedUseCase_noSoliInRange_returnsMonthlyInvoice(self):
        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE, result)

    def test_getIntendedUseCase_soliExistsButNoSubscriptions_returnsSoliOnly(self):
        SolidarityContributionFactory.create(
            member=self.payment.mandate_ref.member,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(
            ParameterKeys.PAYMENT_INTENDED_USE_SOLI_CONTRIBUTION_ONLY, result
        )

    def test_getIntendedUseCase_soliNegativeAndSubscriptions_returnsSoliSupported(self):
        SolidarityContributionFactory.create(
            member=self.payment.mandate_ref.member,
            start_date=self.growing_period.start_date,
            amount=-5,
        )
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(
            ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE_SOLIDARITY_SUPPORTED,
            result,
        )

    def test_getIntendedUseCase_soliPositiveAndSubscriptions_returnsMonthlyInvoice(
        self,
    ):
        SolidarityContributionFactory.create(
            member=self.payment.mandate_ref.member,
            start_date=self.growing_period.start_date,
            amount=5,
        )
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(
            ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE,
            result,
        )
