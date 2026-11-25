import datetime
from decimal import Decimal

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_STATUS_ACTIVE,
)
from tapir.bidding_round.tests.factories import (
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.wirgarten.models import Product
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, ProductFactory
from tapir.wirgarten.utils import get_now


def create_open_round(
    target_amount_per_year=Decimal("1000.00"),
    bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE,
    bid_levels=1,
):
    bidding_round = BiddingRoundFactory.create(
        status=BIDDING_ROUND_STATUS_ACTIVE,
        bidding_procedure=bidding_procedure,
        bid_levels=bid_levels,
        start_at=get_now(cache={}) - datetime.timedelta(hours=1),
        end_at=get_now(cache={}) + datetime.timedelta(days=1),
        growing_period=GrowingPeriodFactory.create(),
        target_amount_per_year=target_amount_per_year,
    )
    product = ProductFactory.create(type=bidding_round.product_type)
    BiddingRoundProductPriceFactory.create(
        round=bidding_round,
        product=product,
        reference_value=Decimal("90.00"),
        min_amount=Decimal("70.00"),
    )
    return bidding_round


def get_product_for_round(bidding_round) -> Product:
    return Product.objects.filter(type_id=bidding_round.product_type_id).first()


def bid_range_payload(bidding_round, amounts=("70.00", "90.00"), quantity=1):
    product = get_product_for_round(bidding_round)
    return {
        "product_id": product.id,
        "quantity": quantity,
        "amount_1": amounts[0],
        "amount_2": amounts[1],
        "cancellation_policy_read": True,
        "contract_accepted": True,
        "privacy_policy_read": True,
    }


def bid_payload(bidding_round, amount="80.00", quantity=1):
    product = get_product_for_round(bidding_round)
    return {
        "product_id": product.id,
        "quantity": quantity,
        "amount_1": amount,
        "cancellation_policy_read": True,
        "contract_accepted": True,
        "privacy_policy_read": True,
    }
