import datetime

from tapir.bidding_round.config import ACTIVE
from tapir.bidding_round.tests.factories import (
    BiddingRoundFactory,
    BiddingRoundProductFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.wirgarten.tests.factories import (
    ProductCapacityFactory,
    ProductFactory,
)
from tapir.wirgarten.utils import get_now


def create_open_round(bid_levels=1, bidding_procedure=None):
    now = get_now()
    if bidding_procedure is not None:
        return BiddingRoundFactory.create(
            status=ACTIVE,
            start_at=now - datetime.timedelta(days=1),
            end_at=now + datetime.timedelta(days=10),
            bid_levels=bid_levels,
            bidding_procedure=bidding_procedure,
        )
    return BiddingRoundFactory.create(
        status=ACTIVE,
        start_at=now - datetime.timedelta(days=1),
        end_at=now + datetime.timedelta(days=10),
        bid_levels=bid_levels,
    )


def build_item(
    round_product,
    product,
    quantity=1,
    amount_1="80.00",
    amount_2=None,
    amount_3=None,
):
    item = {
        "round_product_id": round_product.id,
        "product_id": product.id,
        "quantity": quantity,
    }
    if amount_1 is not None:
        item["amount_1"] = amount_1
    if amount_2 is not None:
        item["amount_2"] = amount_2
    if amount_3 is not None:
        item["amount_3"] = amount_3
    return item


def create_round_product_with_product(
    round_,
    reference_value=None,
    min_amount=None,
    target_amount_per_year=None,
    capacity=100,
):
    round_product = BiddingRoundProductFactory.create(
        round=round_, target_amount_per_year=target_amount_per_year
    )
    ProductCapacityFactory.create(
        period=round_.growing_period,
        product_type=round_product.product_type,
        capacity=capacity,
    )
    product = ProductFactory.create(type=round_product.product_type)
    BiddingRoundProductPriceFactory.create(
        round_product=round_product,
        product=product,
        reference_value=reference_value,
        min_amount=min_amount,
    )
    return round_product, product
