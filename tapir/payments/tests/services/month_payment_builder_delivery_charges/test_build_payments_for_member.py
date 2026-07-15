import datetime
from decimal import Decimal

from tapir.configuration.models import TapirParameter
from tapir.deliveries.tests.factories import JokerFactory
from tapir.payments.models import MemberPaymentRhythm
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

MONTHLY = MemberPaymentRhythm.Rhythm.MONTHLY.value


class TestBuildPaymentsForMember(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value="2")
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value=True
        )
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_START_DATE).update(
            value="2026-01-01"
        )

        cls.first_of_month = datetime.date(year=2026, month=5, day=1)

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

    def _make_member_at_location(self, pickup_location):
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        return member

    def _make_subscription(self, member):
        return SubscriptionFactory.create(
            member=member,
            product=self.product,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

    def test_buildPaymentsForMember_singleLocation_returnsOnePaymentForTheWholeSpan(
        self,
    ):
        member = self._make_member_at_location(self.pickup_location_a)
        subscription = self._make_subscription(member)
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location_a,
            amount=Decimal("3.50"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )

        payments = MonthPaymentBuilderDeliveryCharges.build_payments_for_member(
            member=member,
            contracts={subscription},
            first_of_month=self.first_of_month,
            rhythm=MONTHLY,
            cache={},
            generated_payments=set(),
            in_trial=False,
        )

        self.assertEqual(1, len(payments))
        payment = payments[0]
        # 4 Wednesdays in May 2026 * 3.50
        self.assertEqual(Decimal("14.00"), payment.amount)
        self.assertEqual(
            datetime.date(year=2026, month=5, day=6),
            payment.subscription_payment_range_start,
        )
        self.assertEqual(
            datetime.date(year=2026, month=5, day=27),
            payment.subscription_payment_range_end,
        )
        self.assertEqual(
            MonthPaymentBuilderDeliveryCharges.PAYMENT_TYPE_DELIVERY_CHARGE,
            payment.type,
        )
        self.assertEqual(self.pickup_location_a.id, payment.pickup_location_id)

    def test_buildPaymentsForMember_movesMidMonth_returnsOnePaymentPerLocation(self):
        member = self._make_member_at_location(self.pickup_location_a)
        # From May 14 on, the member is assigned to location B. Deliveries are on
        # Wednesdays: May 6 + 13 at A, May 20 + 27 at B.
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location_b,
            valid_from=datetime.date(year=2026, month=5, day=14),
        )
        subscription = self._make_subscription(member)
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location_a,
            amount=Decimal("3.50"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location_b,
            amount=Decimal("2.00"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )

        payments = MonthPaymentBuilderDeliveryCharges.build_payments_for_member(
            member=member,
            contracts={subscription},
            first_of_month=self.first_of_month,
            rhythm=MONTHLY,
            cache={},
            generated_payments=set(),
            in_trial=False,
        )

        self.assertEqual(2, len(payments))
        payments_by_start = {
            payment.subscription_payment_range_start: payment for payment in payments
        }

        payment_a = payments_by_start[datetime.date(year=2026, month=5, day=6)]
        self.assertEqual(Decimal("7.00"), payment_a.amount)
        self.assertEqual(
            datetime.date(year=2026, month=5, day=13),
            payment_a.subscription_payment_range_end,
        )
        self.assertEqual(self.pickup_location_a.id, payment_a.pickup_location_id)

        payment_b = payments_by_start[datetime.date(year=2026, month=5, day=20)]
        self.assertEqual(Decimal("4.00"), payment_b.amount)
        self.assertEqual(
            datetime.date(year=2026, month=5, day=27),
            payment_b.subscription_payment_range_end,
        )
        self.assertEqual(self.pickup_location_b.id, payment_b.pickup_location_id)

    def test_buildPaymentsForMember_returnsToFormerLocationThenRerun_doesNotDoubleBill(
        self,
    ):
        # A -> B -> A within the same month, so A's date span [May 6, May 27]
        # contains B's span [May 13, May 20]. A range-only already_paid lookup
        # would let the two locations contaminate each other on the second run;
        # scoping by pickup location must keep them independent.
        member = self._make_member_at_location(self.pickup_location_a)
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location_b,
            valid_from=datetime.date(year=2026, month=5, day=11),
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location_a,
            valid_from=datetime.date(year=2026, month=5, day=25),
        )
        subscription = self._make_subscription(member)
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location_a,
            amount=Decimal("3.50"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location_b,
            amount=Decimal("2.00"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )

        first_run = MonthPaymentBuilderDeliveryCharges.build_payments_for_member(
            member=member,
            contracts={subscription},
            first_of_month=self.first_of_month,
            rhythm=MONTHLY,
            cache={},
            generated_payments=set(),
            in_trial=False,
        )
        self.assertEqual(2, len(first_run))
        amounts_by_location = {
            payment.pickup_location_id: payment.amount for payment in first_run
        }
        # A: May 6 + May 27 = 2 * 3.50; B: May 13 + May 20 = 2 * 2.00
        self.assertEqual(
            Decimal("7.00"), amounts_by_location[self.pickup_location_a.id]
        )
        self.assertEqual(
            Decimal("4.00"), amounts_by_location[self.pickup_location_b.id]
        )

        Payment.objects.bulk_create(first_run)

        second_run = MonthPaymentBuilderDeliveryCharges.build_payments_for_member(
            member=member,
            contracts={subscription},
            first_of_month=self.first_of_month,
            rhythm=MONTHLY,
            cache={},
            generated_payments=set(),
            in_trial=False,
        )

        self.assertEqual([], second_run)

    def test_buildPaymentsForMember_allDeliveriesAtLocationJokeredAfterBilling_refundsIt(
        self,
    ):
        member = self._make_member_at_location(self.pickup_location_a)
        subscription = self._make_subscription(member)
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location_a,
            amount=Decimal("3.50"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )

        first_run = MonthPaymentBuilderDeliveryCharges.build_payments_for_member(
            member=member,
            contracts={subscription},
            first_of_month=self.first_of_month,
            rhythm=MONTHLY,
            cache={},
            generated_payments=set(),
            in_trial=False,
        )
        self.assertEqual(1, len(first_run))
        self.assertEqual(Decimal("14.00"), first_run[0].amount)
        Payment.objects.bulk_create(first_run)

        for day in [6, 13, 20, 27]:
            JokerFactory.create(
                member=member, date=datetime.date(year=2026, month=5, day=day)
            )

        second_run = MonthPaymentBuilderDeliveryCharges.build_payments_for_member(
            member=member,
            contracts={subscription},
            first_of_month=self.first_of_month,
            rhythm=MONTHLY,
            cache={},
            generated_payments=set(),
            in_trial=False,
        )

        self.assertEqual(1, len(second_run))
        refund = second_run[0]
        self.assertEqual(Decimal("-14.00"), refund.amount)
        self.assertEqual(self.pickup_location_a.id, refund.pickup_location_id)
