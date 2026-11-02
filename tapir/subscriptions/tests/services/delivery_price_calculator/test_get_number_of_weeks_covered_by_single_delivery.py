from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.constants import (
    WEEKLY,
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
    CUSTOM_CYCLE,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetNumberOfWeeksCoveredBySingleDelivery(TapirUnitTest):
    def test_getNumberOfWeeksCoveredBySingleDelivery_default_returnsWeeksPerCycle(
        self,
    ):
        for delivery_cycle, expected in [
            (WEEKLY[0], 1),
            (ODD_WEEKS[0], 2),
            (EVEN_WEEKS[0], 2),
            (EVERY_FOUR_WEEKS[0], 4),
            (CUSTOM_CYCLE[0], 1),
        ]:
            with self.subTest(delivery_cycle=delivery_cycle):
                self.assertEqual(
                    expected,
                    DeliveryPriceCalculator.get_number_of_weeks_covered_by_single_delivery(
                        delivery_cycle
                    ),
                )
