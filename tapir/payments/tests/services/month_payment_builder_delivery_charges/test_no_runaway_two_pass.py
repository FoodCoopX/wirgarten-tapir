import datetime
from decimal import Decimal

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberCredit, MemberPaymentRhythm
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.pickup_locations.tests.factories import PickupLocationDeliveryChargeFactory
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import Payment, PickupLocationOpeningTime
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductFactory,
    ProductPriceFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestNoRunawayTwoPass(TapirIntegrationTest):
    """
    A yearly-rhythm member billed for the whole year who then gains a second
    subscription mid-year (which enters its trial period) must not produce a
    spurious refund on the next payment run. The two-pass split bills the same
    dates in two differently-sized windows, but because the delivery-charge
    builder never emits a negative amount, the daily rerun stays a converging
    fixpoint and no MemberCredit is ever created here.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value="2")
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_START_DATE).update(
            value="2026-01-01"
        )
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM).update(
            value=MemberPaymentRhythm.Rhythm.YEARLY.value
        )

        cls.current_month = datetime.date(year=2026, month=5, day=1)
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        cls.pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=cls.pickup_location,
            day_of_week=2,
            open_time=datetime.time(hour=14),
            close_time=datetime.time(hour=18),
        )
        cls.product_type = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        cls.product = ProductFactory.create(type=cls.product_type)
        ProductPriceFactory.create(
            product=cls.product, valid_from=datetime.date(year=2026, month=1, day=1)
        )
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=cls.pickup_location,
            amount=Decimal("3.50"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )

    def setUp(self):
        # Member creation reaches the Keycloak client, which is only mocked by
        # TapirIntegrationTest.setUp (per instance), not in setUpTestData.
        super().setUp()
        self.member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        SubscriptionFactory.create(
            member=self.member,
            product=self.product,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

    def _run_both_passes(self):
        in_trial_payments = (
            MonthPaymentBuilderDeliveryCharges.build_payments_for_delivery_charges(
                current_month=self.current_month,
                cache={},
                generated_payments=set(),
                in_trial=True,
            )
        )
        not_in_trial_payments = (
            MonthPaymentBuilderDeliveryCharges.build_payments_for_delivery_charges(
                current_month=self.current_month,
                cache={},
                generated_payments=set(in_trial_payments),
                in_trial=False,
            )
        )
        return in_trial_payments + not_in_trial_payments

    def test_buildPaymentsForDeliveryCharges_yearlyMemberGainsSecondSubscription_noSpuriousRefund(
        self,
    ):
        first_run_payments = self._run_both_passes()
        # The whole 2026: all Wednesdays * 3.50, billed up front.
        yearly_amount = sum(payment.amount for payment in first_run_payments)
        self.assertGreater(yearly_amount, Decimal("100.00"))
        Payment.objects.bulk_create(first_run_payments)

        # A second subscription is added mid-year on the same delivery dates
        # (this is what a subscription entering the trial period looks like).
        SubscriptionFactory.create(
            member=self.member,
            product=self.product,
            start_date=datetime.date(year=2026, month=6, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

        second_run_payments = self._run_both_passes()

        self.assertEqual([], second_run_payments)
        self.assertEqual(0, MemberCredit.objects.count())
