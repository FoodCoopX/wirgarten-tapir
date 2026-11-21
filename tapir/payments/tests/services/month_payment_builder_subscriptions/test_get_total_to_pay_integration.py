import datetime
from decimal import Decimal

from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import GrowingPeriod, Subscription, Product, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    PickupLocationOpeningTimesFactory,
    ProductFactory,
    ProductPriceFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetTotalToPayIntegration(TapirIntegrationTest):
    # October 2026 has 5 Thursdays (1, 8, 15, 22, 29), November 2026 has 4.
    MONDAY = 0
    THURSDAY = 3

    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.growing_period_2026 = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1)
        )
        cls.growing_period_2027 = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1)
        )
        product_type = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        cls.medium_box = cls._create_product(
            product_type=product_type, name="M", price=95
        )
        cls.small_box = cls._create_product(
            product_type=product_type, name="S", price=65
        )

    @staticmethod
    def _create_product(product_type: ProductType, name: str, price: int) -> Product:
        product = ProductFactory.create(type=product_type, name=name)
        ProductPriceFactory.create(
            product=product,
            price=price,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        return product

    def setUp(self) -> None:
        super().setUp()
        self._set_parameter(
            key=ParameterKeys.PAYMENT_PARTIAL_MONTH_PROPORTIONAL_START_DATE,
            value=datetime.date(year=2026, month=1, day=1),
        )
        self.member = MemberFactory.create()
        self._move_member_to_location_with_delivery_on(
            day_of_week=self.THURSDAY,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )

    def _move_member_to_location_with_delivery_on(
        self, day_of_week: int, valid_from: datetime.date
    ) -> None:
        pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTimesFactory.create(
            pickup_location=pickup_location, day_of_week=day_of_week
        )
        MemberPickupLocationFactory.create(
            member=self.member, pickup_location=pickup_location, valid_from=valid_from
        )

    def _create_subscription(
        self,
        product: Product,
        start_date: datetime.date,
        end_date: datetime.date,
        quantity: int = 1,
    ) -> Subscription:
        return SubscriptionFactory.create(
            member=self.member,
            product=product,
            quantity=quantity,
            period=self._get_growing_period(start_date=start_date),
            start_date=start_date,
            end_date=end_date,
        )

    def _get_growing_period(self, start_date: datetime.date) -> GrowingPeriod:
        if start_date.year == 2026:
            return self.growing_period_2026
        return self.growing_period_2027

    @staticmethod
    def _get_total_to_pay(
        contracts: list[Subscription],
        range_start: datetime.date,
        range_end: datetime.date,
    ) -> Decimal:
        return MonthPaymentBuilderSubscriptions.get_total_to_pay(
            range_start=range_start,
            range_end=range_end,
            contracts=contracts,
            cache={},
        )

    def _get_total_to_pay_for_october_2026(
        self, contracts: list[Subscription]
    ) -> Decimal:
        return self._get_total_to_pay(
            contracts=contracts,
            range_start=datetime.date(year=2026, month=10, day=1),
            range_end=datetime.date(year=2026, month=10, day=31),
        )

    def test_getTotalToPay_changeWithPriceChangeInMonthWithFiveDates_returnsShareOfEachContract(
        self,
    ):
        contracts = [
            self._create_subscription(
                product=self.medium_box,
                quantity=2,
                start_date=datetime.date(year=2026, month=1, day=1),
                end_date=datetime.date(year=2026, month=10, day=26),
            ),
            self._create_subscription(
                product=self.medium_box,
                start_date=datetime.date(year=2026, month=10, day=27),
                end_date=datetime.date(year=2026, month=12, day=31),
            ),
            self._create_subscription(
                product=self.small_box,
                start_date=datetime.date(year=2026, month=10, day=27),
                end_date=datetime.date(year=2026, month=12, day=31),
            ),
        ]

        # 4/5 × 190 + 1/5 × 95 + 1/5 × 65
        self.assertEqual(
            Decimal("184.00"),
            self._get_total_to_pay_for_october_2026(contracts).quantize(
                Decimal("0.01")
            ),
        )

    def test_getTotalToPay_twoChangesWithoutPriceChangeInSameMonth_returnsMonthlyPrice(
        self,
    ):
        contracts = [
            self._create_subscription(
                product=self.medium_box,
                start_date=datetime.date(year=2026, month=1, day=1),
                end_date=datetime.date(year=2026, month=10, day=7),
            ),
            self._create_subscription(
                product=self.medium_box,
                start_date=datetime.date(year=2026, month=10, day=8),
                end_date=datetime.date(year=2026, month=10, day=21),
            ),
            self._create_subscription(
                product=self.medium_box,
                start_date=datetime.date(year=2026, month=10, day=22),
                end_date=datetime.date(year=2026, month=12, day=31),
            ),
        ]

        self.assertEqual(
            Decimal("95.00"),
            self._get_total_to_pay_for_october_2026(contracts).quantize(
                Decimal("0.01")
            ),
        )

    def test_getTotalToPay_contractStartsAfterDeliveryFreeWeeks_deliveryFreeWeeksCountAsDeliveryDates(
        self,
    ):
        GrowingPeriod.objects.filter(id=self.growing_period_2027.id).update(
            weeks_without_delivery=[1, 2]
        )
        contract = self._create_subscription(
            product=self.medium_box,
            start_date=datetime.date(year=2027, month=1, day=25),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        # Thursdays of January 2027: 7 (KW 1), 14 (KW 2), 21, 28 → 1/4 × 95
        self.assertEqual(
            Decimal("23.75"),
            self._get_total_to_pay(
                contracts=[contract],
                range_start=datetime.date(year=2027, month=1, day=1),
                range_end=datetime.date(year=2027, month=1, day=31),
            ).quantize(Decimal("0.01")),
        )

    def test_getTotalToPay_pickupLocationChangeWithinMonth_usesLocationOfEachWeek(
        self,
    ):
        self._move_member_to_location_with_delivery_on(
            day_of_week=self.MONDAY,
            valid_from=datetime.date(year=2026, month=10, day=19),
        )
        contract = self._create_subscription(
            product=self.medium_box,
            start_date=datetime.date(year=2026, month=10, day=20),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

        # Thursday 1, 8, 15, then Monday 19, 26 → 1/5 × 95
        self.assertEqual(
            Decimal("19.00"),
            self._get_total_to_pay_for_october_2026([contract]).quantize(
                Decimal("0.01")
            ),
        )

    def test_getTotalToPay_noPickupLocationBeforeContractStart_weeksBeforeContractUseLocationOfContract(
        self,
    ):
        self.member = MemberFactory.create()
        self._move_member_to_location_with_delivery_on(
            day_of_week=self.THURSDAY,
            valid_from=datetime.date(year=2027, month=1, day=18),
        )
        self._move_member_to_location_with_delivery_on(
            day_of_week=self.MONDAY,
            valid_from=datetime.date(year=2027, month=3, day=1),
        )
        contract = self._create_subscription(
            product=self.medium_box,
            start_date=datetime.date(year=2027, month=1, day=18),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        # Thursdays of January 2027: 7, 14, 21, 28. Thursday 31.12.2026 is in December.
        # 2/4 × 95
        self.assertEqual(
            Decimal("47.50"),
            self._get_total_to_pay(
                contracts=[contract],
                range_start=datetime.date(year=2027, month=1, day=1),
                range_end=datetime.date(year=2027, month=1, day=31),
            ).quantize(Decimal("0.01")),
        )

    def test_getTotalToPay_rangeSpansCutoff_appliesOldRuleBeforeAndNewRuleFromCutoff(
        self,
    ):
        self._set_parameter(
            key=ParameterKeys.PAYMENT_PARTIAL_MONTH_PROPORTIONAL_START_DATE,
            value=datetime.date(year=2027, month=1, day=1),
        )
        contract = self._create_subscription(
            product=self.medium_box,
            start_date=datetime.date(year=2026, month=10, day=15),
            end_date=datetime.date(year=2027, month=1, day=13),
        )

        # October, old rule: 3 deliveries × 95 × 12 ÷ 53 weeks
        # November and December: 2 × 95
        # January, new rule: 1/4 × 95
        self.assertEqual(
            Decimal("278.28"),
            self._get_total_to_pay(
                contracts=[contract],
                range_start=datetime.date(year=2026, month=10, day=1),
                range_end=datetime.date(year=2027, month=1, day=31),
            ).quantize(Decimal("0.01")),
        )
