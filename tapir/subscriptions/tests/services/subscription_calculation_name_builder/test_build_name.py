from decimal import Decimal

from tapir.subscriptions.services.subscription_calculation_name_builder import (
    SubscriptionCalculationNameBuilder,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildName(TapirUnitTest):
    @staticmethod
    def _build_subscription(
        quantity: int, price_override: Decimal | None
    ) -> Subscription:
        return SubscriptionFactory.build(
            product__name="Kiste",
            product__type__name="Ernteanteil",
            quantity=quantity,
            price_override=price_override,
        )

    def test_buildName_singleShare_returnsTypeAndProductName(self):
        result = SubscriptionCalculationNameBuilder.build_name(
            subscription=self._build_subscription(quantity=1, price_override=None)
        )

        self.assertEqual("Ernteanteil Kiste", result)

    def test_buildName_severalShares_addsQuantity(self):
        result = SubscriptionCalculationNameBuilder.build_name(
            subscription=self._build_subscription(quantity=2, price_override=None)
        )

        self.assertEqual("Ernteanteil Kiste (2 Anteile)", result)

    def test_buildName_priceOverride_addsSonderpreisInsteadOfQuantity(self):
        result = SubscriptionCalculationNameBuilder.build_name(
            subscription=self._build_subscription(
                quantity=2, price_override=Decimal(80)
            )
        )

        self.assertEqual("Ernteanteil Kiste (Sonderpreis)", result)
