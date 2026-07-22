import datetime

from tapir.configuration.models import TapirParameter
from tapir.deliveries.tests.factories import DeliveryDonationFactory, JokerFactory
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.wirgarten.constants import NO_DELIVERY, WEEKLY
from tapir.wirgarten.models import PickupLocationOpeningTime
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

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
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

    def test_getBillableDeliveryDatesInRange_memberHasJokerInWeek_thatDeliveryStillBilled(
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

        self.assertIn(datetime.date(year=2026, month=5, day=13), result)
        self.assertEqual(4, len(result))

    def test_getBillableDeliveryDatesInRange_productTypeWithoutDelivery_contributesNoDates(
        self,
    ):
        no_delivery_type = ProductTypeFactory.create(delivery_cycle=NO_DELIVERY[0])
        no_delivery_product = ProductFactory.create(type=no_delivery_type)
        ProductPriceFactory.create(
            product=no_delivery_product,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        no_delivery_subscription = self._make_subscription(product=no_delivery_product)

        result = (
            MonthPaymentBuilderDeliveryCharges.get_billable_delivery_dates_in_range(
                subscriptions=[no_delivery_subscription],
                range_start=self.range_start,
                range_end=self.range_end,
                cache={},
            )
        )

        self.assertEqual(set(), result)

    def test_getBillableDeliveryDatesInRange_memberHasDonationInWeek_thatDeliveryStillBilled(
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

        self.assertIn(datetime.date(year=2026, month=5, day=20), result)
        self.assertEqual(4, len(result))

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
