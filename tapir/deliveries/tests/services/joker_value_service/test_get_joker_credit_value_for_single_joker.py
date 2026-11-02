import datetime
from decimal import Decimal

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.pickup_locations.tests.factories import PickupLocationDeliveryChargeFactory
from tapir.solidarity_contribution.tests.factories import (
    SolidarityContributionFactory,
)
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, ODD_WEEKS
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    ProductPriceFactory,
    MemberFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetJokerCreditValueForSingleJoker(TapirIntegrationTest):
    # 15.01.2020 is in the odd week 3, 2020 has 53 weeks
    JOKER_DATE = datetime.date(year=2020, month=1, day=15)

    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )
        cls.weekly_product = cls.create_product(
            delivery_cycle=WEEKLY[0], name="Weekly", price=10, type_name="Type"
        )

    @staticmethod
    def create_product(
        delivery_cycle: str, name: str, price: int, type_name: str | None = None
    ):
        product = ProductFactory.create(
            type__delivery_cycle=delivery_cycle,
            type__name=type_name or f"Type {name}",
            name=name,
        )
        ProductPriceFactory.create(
            product=product,
            valid_from=datetime.date(year=2020, month=1, day=1),
            price=price,
        )
        return product

    def setUp(self) -> None:
        super().setUp()
        self.member = MemberFactory.create()

    def create_subscription(self, product, quantity: int):
        SubscriptionFactory.create(
            member=self.member,
            product=product,
            quantity=quantity,
            period=self.growing_period,
        )

    def create_contribution(self, amount: Decimal):
        SolidarityContributionFactory.create(
            member=self.member,
            amount=amount,
            start_date=datetime.date(year=2020, month=1, day=1),
        )

    def configure_solidarity_contribution_product_type(self, product):
        self._set_parameter(
            key=ParameterKeys.JOKERS_SOLIDARITY_CONTRIBUTION_PRODUCT_TYPE,
            value=product.type.id,
        )

    def get_value(self):
        return JokerValueService.get_joker_credit_value_for_single_joker(
            member=self.member, joker_date=self.JOKER_DATE, cache={}
        )

    def test_getJokerCreditValue_noProductTypeSelected_contributionIgnored(self):
        self.create_subscription(product=self.weekly_product, quantity=1)
        self.create_contribution(amount=Decimal(20))

        self.assertAlmostEqual(Decimal("2.26"), self.get_value(), places=2)

    def test_getJokerCreditValue_positiveContribution_contributionAdded(self):
        self.configure_solidarity_contribution_product_type(self.weekly_product)
        self.create_subscription(product=self.weekly_product, quantity=1)
        self.create_contribution(amount=Decimal(20))

        # (10 + 20) * 12 / 53
        self.assertAlmostEqual(Decimal("6.79"), self.get_value(), places=2)

    def test_getJokerCreditValue_negativeContribution_contributionSubtracted(self):
        self.configure_solidarity_contribution_product_type(self.weekly_product)
        self.create_subscription(product=self.weekly_product, quantity=1)
        self.create_contribution(amount=Decimal(-4))

        # (10 - 4) * 12 / 53
        self.assertAlmostEqual(Decimal("1.36"), self.get_value(), places=2)

    def test_getJokerCreditValue_contributionHigherThanPrice_returnsZero(self):
        self.configure_solidarity_contribution_product_type(self.weekly_product)
        self.create_subscription(product=self.weekly_product, quantity=1)
        self.create_contribution(amount=Decimal(-15))

        self.assertEqual(Decimal(0), self.get_value())

    def test_getJokerCreditValue_noContribution_onlySubscriptionPrice(self):
        self.configure_solidarity_contribution_product_type(self.weekly_product)
        self.create_subscription(product=self.weekly_product, quantity=1)

        self.assertAlmostEqual(Decimal("2.26"), self.get_value(), places=2)

    def test_getJokerCreditValue_severalShares_contributionCountedOnce(self):
        self.configure_solidarity_contribution_product_type(self.weekly_product)
        self.create_subscription(product=self.weekly_product, quantity=3)
        self.create_contribution(amount=Decimal(20))

        # (10 * 3 + 20) * 12 / 53
        self.assertAlmostEqual(Decimal("11.32"), self.get_value(), places=2)

    def test_getJokerCreditValue_selectedTypeDeliveredEveryTwoWeeks_contributionDoubled(
        self,
    ):
        odd_weeks_product = self.create_product(
            delivery_cycle=ODD_WEEKS[0], name="Odd", price=10
        )
        self.configure_solidarity_contribution_product_type(odd_weeks_product)
        self.create_subscription(product=odd_weeks_product, quantity=1)
        self.create_contribution(amount=Decimal(20))

        # (10 + 20) * 12 / 53 * 2
        self.assertAlmostEqual(Decimal("13.58"), self.get_value(), places=2)

    def test_getJokerCreditValue_selectedTypeNotDeliveredInJokerWeek_contributionIgnored(
        self,
    ):
        even_weeks_product = self.create_product(
            delivery_cycle=EVEN_WEEKS[0], name="Even", price=10
        )
        self.configure_solidarity_contribution_product_type(even_weeks_product)
        self.create_subscription(product=self.weekly_product, quantity=1)
        self.create_subscription(product=even_weeks_product, quantity=1)
        self.create_contribution(amount=Decimal(20))

        self.assertAlmostEqual(Decimal("2.26"), self.get_value(), places=2)

    def test_getJokerCreditValue_memberHasNoSubscriptionOfSelectedType_contributionIgnored(
        self,
    ):
        other_product = self.create_product(
            delivery_cycle=WEEKLY[0], name="Other", price=10
        )
        self.configure_solidarity_contribution_product_type(other_product)
        self.create_subscription(product=self.weekly_product, quantity=1)
        self.create_contribution(amount=Decimal(20))

        self.assertAlmostEqual(Decimal("2.26"), self.get_value(), places=2)

    def test_getJokerCreditValue_selectedTypeDoesNotExist_contributionIgnored(self):
        self._set_parameter(
            key=ParameterKeys.JOKERS_SOLIDARITY_CONTRIBUTION_PRODUCT_TYPE,
            value="deleted_product_type_id",
        )
        self.create_subscription(product=self.weekly_product, quantity=1)
        self.create_contribution(amount=Decimal(20))

        self.assertAlmostEqual(Decimal("2.26"), self.get_value(), places=2)

    def test_getJokerCreditValue_pickupLocationHasDeliveryCharge_chargeAdded(self):
        self.configure_solidarity_contribution_product_type(self.weekly_product)
        self.create_subscription(product=self.weekly_product, quantity=1)
        self.create_contribution(amount=Decimal(20))
        pickup_location = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=pickup_location,
            valid_from=datetime.date(year=2020, month=1, day=1),
        )
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=pickup_location,
            amount=Decimal("1.50"),
            valid_from=datetime.date(year=2020, month=1, day=1),
        )

        # (10 + 20) * 12 / 53 + 1.50
        self.assertAlmostEqual(Decimal("8.29"), self.get_value(), places=2)
