import datetime
from decimal import Decimal

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
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


class TestBuildRefundCreditsForPickupLocationChange(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value="2")
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_START_DATE).update(
            value="2026-01-01"
        )
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM).update(
            value=MemberPaymentRhythm.Rhythm.MONTHLY.value
        )

        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

        cls.pickup_location_a = PickupLocationFactory.create()
        cls.pickup_location_b = PickupLocationFactory.create()
        for pickup_location in [cls.pickup_location_a, cls.pickup_location_b]:
            PickupLocationOpeningTime.objects.create(
                pickup_location=pickup_location,
                day_of_week=2,
                open_time=datetime.time(hour=14),
                close_time=datetime.time(hour=18),
            )

        cls.product_type = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        cls.product = ProductFactory.create(type=cls.product_type)
        ProductPriceFactory.create(
            product=cls.product,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=cls.pickup_location_a,
            amount=Decimal("3.50"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )

    def _prepay_month_at_location_a(self, member, subscription):
        payments = MonthPaymentBuilderDeliveryCharges.build_payments_for_member(
            member=member,
            contracts={subscription},
            first_of_month=datetime.date(year=2026, month=5, day=1),
            rhythm=MemberPaymentRhythm.Rhythm.MONTHLY.value,
            in_trial=False,
            cache={},
            generated_payments=set(),
        )
        Payment.objects.bulk_create(payments)
        return payments

    def _make_member_with_prepaid_may(self):
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location_a,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        payments = self._prepay_month_at_location_a(member, subscription)
        # 4 Wednesdays in May 2026 * 3.50
        self.assertEqual(Decimal("14.00"), payments[0].amount)
        return member

    def test_buildRefundCredits_movesToChargeFreeLocationMidMonth_refundsRemainingPrepaidCharge(
        self,
    ):
        member = self._make_member_with_prepaid_may()
        # From May 14 the member is at B (no delivery charge): A keeps only
        # May 6 + 13 (7.00 owed) of the 14.00 prepaid, so 7.00 is refunded.
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location_b,
            valid_from=datetime.date(year=2026, month=5, day=14),
        )

        credits = MonthPaymentBuilderDeliveryCharges.build_refund_credits_for_pickup_location_change(
            member=member,
            reference_date=datetime.date(year=2026, month=5, day=14),
            cache={},
        )

        self.assertEqual(1, len(credits))
        credit = credits[0]
        self.assertEqual(Decimal("7.00"), credit.amount)
        self.assertEqual(self.pickup_location_a.id, credit.pickup_location_id)
        self.assertEqual(member.id, credit.member_id)
        self.assertEqual(
            MonthPaymentBuilderDeliveryCharges.PAYMENT_TYPE_DELIVERY_CHARGE,
            credit.source,
        )

    def test_buildRefundCredits_pastPaymentHasNoPickupLocation_ignoresItAndDoesNotCrash(
        self,
    ):
        member = self._make_member_with_prepaid_may()
        # A stray delivery-charge payment with no pickup location (e.g. a row
        # from before the pickup_location field existed) must not crash the
        # refund and must not become a credit for a nonexistent location.
        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache={}
        )
        Payment.objects.create(
            due_date=datetime.date(year=2026, month=5, day=1),
            amount=Decimal("5.00"),
            mandate_ref=mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=MonthPaymentBuilderDeliveryCharges.PAYMENT_TYPE_DELIVERY_CHARGE,
            subscription_payment_range_start=datetime.date(year=2026, month=5, day=6),
            subscription_payment_range_end=datetime.date(year=2026, month=5, day=27),
            pickup_location=None,
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location_b,
            valid_from=datetime.date(year=2026, month=5, day=14),
        )

        credits = MonthPaymentBuilderDeliveryCharges.build_refund_credits_for_pickup_location_change(
            member=member,
            reference_date=datetime.date(year=2026, month=5, day=14),
            cache={},
        )

        self.assertEqual(1, len(credits))
        self.assertEqual(self.pickup_location_a.id, credits[0].pickup_location_id)
        self.assertEqual(Decimal("7.00"), credits[0].amount)

    def test_buildRefundCredits_noOverpayment_returnsNoCredit(self):
        member = self._make_member_with_prepaid_may()
        # The member stays at A: they owe exactly what they prepaid, no refund.
        credits = MonthPaymentBuilderDeliveryCharges.build_refund_credits_for_pickup_location_change(
            member=member,
            reference_date=datetime.date(year=2026, month=5, day=14),
            cache={},
        )

        self.assertEqual([], credits)

    def test_buildRefundCredits_amountIsNettedByBuilderOnNextRun_soNoDoubleRefund(self):
        member = self._make_member_with_prepaid_may()
        subscription = member.subscription_set.first()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location_b,
            valid_from=datetime.date(year=2026, month=5, day=14),
        )

        credits = MonthPaymentBuilderDeliveryCharges.build_refund_credits_for_pickup_location_change(
            member=member,
            reference_date=datetime.date(year=2026, month=5, day=14),
            cache={},
        )
        from tapir.payments.services.member_credit_creator import MemberCreditCreator

        MemberCreditCreator.save_credits_with_log_entries(credits, actor=None)

        # After the credit is persisted, the daily builder must not bill A again:
        # A owes 7.00, already paid 14.00 minus the 7.00 credit = 7.00, delta 0.
        rerun_payments = MonthPaymentBuilderDeliveryCharges.build_payments_for_member(
            member=member,
            contracts={subscription},
            first_of_month=datetime.date(year=2026, month=5, day=1),
            rhythm=MemberPaymentRhythm.Rhythm.MONTHLY.value,
            in_trial=False,
            cache={},
            generated_payments=set(),
        )

        self.assertNotIn(
            self.pickup_location_a.id,
            {payment.pickup_location_id for payment in rerun_payments},
        )
