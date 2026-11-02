import datetime

from tapir.associations.tests.factories import (
    AssociationMembershipFactory,
    AssociationMembershipTypePriceFactory,
)
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

CANCELLATION_TS = datetime.datetime(
    year=2025, month=1, day=10, tzinfo=datetime.timezone.utc
)


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

    def _set_payment_to_last_month_of_growing_period(self):
        self.payment.subscription_payment_range_start = datetime.date(
            year=2025, month=12, day=1
        )
        self.payment.subscription_payment_range_end = datetime.date(
            year=2025, month=12, day=31
        )

    def _create_membership_type_with_price(self, price):
        return AssociationMembershipTypePriceFactory.create(
            valid_from=self.growing_period.start_date, price=price
        ).type

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

    def test_getIntendedUseCase_subscriptionCancelledAndEndsAtEndOfRange_returnsLastInvoice(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE, result)

    def test_getIntendedUseCase_subscriptionNotCancelledAndEndsAtEndOfRange_returnsMonthlyInvoice(
        self,
    ):
        # In that case it is considered that the subscription will be renewed
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE, result)

    def test_getIntendedUseCase_subscriptionCancelledButNextSubscriptionExists_returnsMonthlyInvoice(
        self,
    ):
        self._set_payment_to_last_month_of_growing_period()
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            cancellation_ts=CANCELLATION_TS,
        )
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2026, month=1, day=1)
            ),
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE, result)

    def test_getIntendedUseCase_lastPaymentIsAlsoMultipleMonthPayment_returnsLastInvoice(
        self,
    ):
        self.payment.subscription_payment_range_end = datetime.date(
            year=2025, month=3, day=31
        )
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE, result)

    def test_getIntendedUseCase_subscriptionCancelledButSoliContinues_returnsMonthlyInvoice(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )
        SolidarityContributionFactory.create(
            member=self.payment.mandate_ref.member,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
            amount=5,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE, result)

    def test_getIntendedUseCase_soliCancelledButSubscriptionContinues_returnsSoliSupported(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
        )
        SolidarityContributionFactory.create(
            member=self.payment.mandate_ref.member,
            start_date=self.growing_period.start_date,
            end_date=self.payment.subscription_payment_range_end,
            amount=-5,
            cancellation_ts=CANCELLATION_TS,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(
            ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE_SOLIDARITY_SUPPORTED,
            result,
        )

    def test_getIntendedUseCase_soliOnlyAndSoliCancelled_returnsLastInvoice(self):
        SolidarityContributionFactory.create(
            member=self.payment.mandate_ref.member,
            start_date=self.growing_period.start_date,
            end_date=self.payment.subscription_payment_range_end,
            amount=5,
            cancellation_ts=CANCELLATION_TS,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE, result)

    def test_getIntendedUseCase_soliOnlyNotCancelledAndEndsAtEndOfGrowingPeriod_returnsSoliOnly(
        self,
    ):
        self._set_payment_to_last_month_of_growing_period()
        SolidarityContributionFactory.create(
            member=self.payment.mandate_ref.member,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
            amount=5,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(
            ParameterKeys.PAYMENT_INTENDED_USE_SOLI_CONTRIBUTION_ONLY, result
        )

    def test_getIntendedUseCase_subscriptionCancelledAndNegativeSoliContinues_returnsLastInvoice(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )
        SolidarityContributionFactory.create(
            member=self.payment.mandate_ref.member,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
            amount=-5,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE, result)

    def test_getIntendedUseCase_subscriptionCancelledButAssociationMembershipContinues_returnsMonthlyInvoice(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )
        AssociationMembershipFactory.create(
            member=self.payment.mandate_ref.member,
            type=self._create_membership_type_with_price(price=5),
            start_date=self.growing_period.start_date,
            end_date=None,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE, result)

    def test_getIntendedUseCase_subscriptionAndAssociationMembershipCancelled_returnsLastInvoice(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )
        AssociationMembershipFactory.create(
            member=self.payment.mandate_ref.member,
            type=self._create_membership_type_with_price(price=5),
            start_date=self.growing_period.start_date,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE, result)

    def test_getIntendedUseCase_associationMembershipOnlyAndCancelled_returnsLastInvoice(
        self,
    ):
        AssociationMembershipFactory.create(
            member=self.payment.mandate_ref.member,
            type=self._create_membership_type_with_price(price=5),
            start_date=self.growing_period.start_date,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE, result)

    def test_getIntendedUseCase_subscriptionCancelledAndFreeAssociationMembershipContinues_returnsLastInvoice(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )
        AssociationMembershipFactory.create(
            member=self.payment.mandate_ref.member,
            type=self._create_membership_type_with_price(price=0),
            start_date=self.growing_period.start_date,
            end_date=None,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE, result)

    def test_getIntendedUseCase_subscriptionCancelledAndEndsWithinRange_returnsLastInvoice(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=datetime.date(year=2025, month=1, day=19),
            cancellation_ts=CANCELLATION_TS,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE, result)

    def test_getIntendedUseCase_cancelledContractEndsAfterRange_returnsMonthlyInvoice(
        self,
    ):
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=self.payment.subscription_payment_range_end,
            cancellation_ts=CANCELLATION_TS,
        )
        SubscriptionFactory.create(
            member=self.payment.mandate_ref.member,
            period=self.growing_period,
            end_date=datetime.date(year=2025, month=6, day=30),
            cancellation_ts=CANCELLATION_TS,
        )

        result = PaymentExportIntendedUseBuilder._get_intended_use_case(
            payment=self.payment, cache={}
        )

        self.assertEqual(ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE, result)
