import datetime
from decimal import Decimal

from tapir.deliveries.tests.factories import DeliveryDonationFactory, JokerFactory
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.wirgarten.constants import WEEKLY
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


class TestGetBillableDeliveryDatesInRange(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        from tapir.configuration.models import TapirParameter

        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value="2")
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value=True
        )
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DONATION_MODE).update(
            value="opt_in"
        )

        cls.range_start = datetime.date(year=2026, month=5, day=1)
        cls.range_end = datetime.date(year=2026, month=5, day=31)

        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

        cls.pickup_location = PickupLocationFactory.create()
        from tapir.wirgarten.models import PickupLocationOpeningTime

        PickupLocationOpeningTime.objects.create(
            pickup_location=cls.pickup_location,
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

        cls.member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=cls.member,
            pickup_location=cls.pickup_location,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )

    def _make_subscription(self, **overrides):
        defaults = {
            "member": self.member,
            "product": self.product,
            "start_date": datetime.date(year=2026, month=1, day=1),
            "end_date": datetime.date(year=2026, month=12, day=31),
        }
        defaults.update(overrides)
        return SubscriptionFactory.create(**defaults)

    def test_getBillableDeliveryDatesInRange_weeklySubscription_returnsAllWednesdaysInRange(
        self,
    ):
        subscription = self._make_subscription()

        result = (
            MonthPaymentBuilderDeliveryCharges.get_billable_delivery_dates_in_range(
                subscriptions=[subscription],
                range_start=self.range_start,
                range_end=self.range_end,
                cache={},
            )
        )

        expected = {
            datetime.date(year=2026, month=5, day=6),
            datetime.date(year=2026, month=5, day=13),
            datetime.date(year=2026, month=5, day=20),
            datetime.date(year=2026, month=5, day=27),
        }
        self.assertEqual(expected, result)

    def test_getBillableDeliveryDatesInRange_twoSubscriptionsSameDeliveryDay_returnsDedupedDates(
        self,
    ):
        subscription_one = self._make_subscription()
        other_product = ProductFactory.create(type=self.product_type)
        ProductPriceFactory.create(
            product=other_product,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        subscription_two = self._make_subscription(product=other_product)

        result = (
            MonthPaymentBuilderDeliveryCharges.get_billable_delivery_dates_in_range(
                subscriptions=[subscription_one, subscription_two],
                range_start=self.range_start,
                range_end=self.range_end,
                cache={},
            )
        )

        self.assertEqual(4, len(result))

    def test_getBillableDeliveryDatesInRange_memberHasJokerInWeek_thatDeliverySkipped(
        self,
    ):
        subscription = self._make_subscription()
        JokerFactory.create(
            member=self.member,
            date=datetime.date(year=2026, month=5, day=13),
        )

        result = (
            MonthPaymentBuilderDeliveryCharges.get_billable_delivery_dates_in_range(
                subscriptions=[subscription],
                range_start=self.range_start,
                range_end=self.range_end,
                cache={},
            )
        )

        self.assertNotIn(datetime.date(year=2026, month=5, day=13), result)
        self.assertEqual(3, len(result))

    def test_getBillableDeliveryDatesInRange_memberHasDonationInWeek_thatDeliverySkipped(
        self,
    ):
        subscription = self._make_subscription()
        DeliveryDonationFactory.create(
            member=self.member,
            date=datetime.date(year=2026, month=5, day=20),
        )

        result = (
            MonthPaymentBuilderDeliveryCharges.get_billable_delivery_dates_in_range(
                subscriptions=[subscription],
                range_start=self.range_start,
                range_end=self.range_end,
                cache={},
            )
        )

        self.assertNotIn(datetime.date(year=2026, month=5, day=20), result)
        self.assertEqual(3, len(result))

    def test_getBillableDeliveryDatesInRange_subscriptionEndsMidRange_returnsOnlyDatesBeforeEnd(
        self,
    ):
        subscription = self._make_subscription(
            end_date=datetime.date(year=2026, month=5, day=15)
        )

        result = (
            MonthPaymentBuilderDeliveryCharges.get_billable_delivery_dates_in_range(
                subscriptions=[subscription],
                range_start=self.range_start,
                range_end=self.range_end,
                cache={},
            )
        )

        self.assertEqual(
            {
                datetime.date(year=2026, month=5, day=6),
                datetime.date(year=2026, month=5, day=13),
            },
            result,
        )

    def test_getBillableDeliveryDatesInRange_subscriptionForOtherMember_notIncluded(
        self,
    ):
        subscription = self._make_subscription()
        other_member = MemberFactory.create()
        other_subscription = SubscriptionFactory.create(
            member=other_member,
            product=self.product,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

        result = (
            MonthPaymentBuilderDeliveryCharges.get_billable_delivery_dates_in_range(
                subscriptions=[subscription, other_subscription],
                range_start=self.range_start,
                range_end=self.range_end,
                cache={},
            )
        )

        self.assertEqual(4, len(result))
