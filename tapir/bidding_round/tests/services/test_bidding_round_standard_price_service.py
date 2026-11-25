import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.bidding_round.services.bidding_round_standard_price_service import (
    BiddingRoundStandardPriceService,
)
from tapir.bidding_round.tests.factories import (
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.wirgarten.models import ProductPrice
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    ProductFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBiddingRoundStandardPriceService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _create_round(self, locked=True, locked_average=Decimal("85.00")):
        start_date = get_now(cache={}).date() + datetime.timedelta(days=30)
        period = GrowingPeriodFactory.create(
            start_date=start_date,
            end_date=start_date + datetime.timedelta(days=364),
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period,
            average_bid_locked_at=get_now(cache={}) if locked else None,
            locked_bidder_average_per_share_per_month=(
                locked_average if locked else None
            ),
        )
        products = [
            ProductFactory.create(type=bidding_round.product_type),
            ProductFactory.create(type=bidding_round.product_type),
        ]
        for product, size in zip(products, [Decimal("1.0"), Decimal("1.7")]):
            BiddingRoundProductPriceFactory.create(
                round=bidding_round,
                product=product,
                size=size,
            )
            ProductPriceFactory.create(
                product=product,
                price=Decimal("70.00"),
                size=Decimal("1.5000"),
                valid_from=period.start_date - datetime.timedelta(days=1),
            )
        return bidding_round, products, period

    def test_alignStandardPrices_default_setsLockedAverageTimesRoundProductSize(self):
        bidding_round, products, period = self._create_round()

        results = BiddingRoundStandardPriceService.align_standard_prices(
            bidding_round, cache={}
        )

        expected_prices = {
            products[0].id: Decimal("85.00"),
            products[1].id: Decimal("144.50"),
        }
        self.assertEqual(2, len(results))
        for result in results:
            self.assertEqual(
                str(expected_prices[result["product_id"]]), result["price"]
            )
        for product in products:
            price = ProductPrice.objects.get(
                product=product, valid_from=period.start_date
            )
            self.assertEqual(expected_prices[product.id], price.price)
            self.assertEqual(Decimal("1.5000"), price.size)

    def test_alignStandardPrices_averageNotLocked_raisesValidationError(self):
        bidding_round, _products, _period = self._create_round(locked=False)

        with self.assertRaises(ValidationError):
            BiddingRoundStandardPriceService.align_standard_prices(
                bidding_round, cache={}
            )

    def test_alignStandardPrices_lockedAverageZero_raisesValidationError(self):
        bidding_round, _products, _period = self._create_round(
            locked_average=Decimal("0.00")
        )

        with self.assertRaises(ValidationError):
            BiddingRoundStandardPriceService.align_standard_prices(
                bidding_round, cache={}
            )

    def test_alignStandardPrices_contractPeriodEnded_raisesValidationError(self):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() - datetime.timedelta(days=400),
            end_date=get_now(cache={}).date() - datetime.timedelta(days=10),
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period,
            average_bid_locked_at=get_now(cache={}),
            locked_bidder_average_per_share_per_month=Decimal("85.00"),
        )

        with self.assertRaises(ValidationError):
            BiddingRoundStandardPriceService.align_standard_prices(
                bidding_round, cache={}
            )
