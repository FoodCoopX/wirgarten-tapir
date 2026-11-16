import datetime
from decimal import Decimal

import factory

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CONFIGURATION
from tapir.bidding_round.models import (
    Bid,
    BidItem,
    BiddingRound,
    BiddingRoundProductPrice,
    BiddingRoundProductType,
)
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    ProductTypeFactory,
)


class BiddingRoundFactory(factory.django.DjangoModelFactory[BiddingRound]):
    class Meta:
        model = BiddingRound

    growing_period = factory.SubFactory(GrowingPeriodFactory)
    name = factory.Faker("sentence", nb_words=2)
    status = BIDDING_ROUND_STATUS_CONFIGURATION
    end_at = factory.LazyAttribute(
        lambda bidding_round: datetime.datetime.combine(
            bidding_round.growing_period.start_date,
            datetime.time(hour=23, minute=59),
            tzinfo=datetime.timezone.utc,
        )
    )


class BiddingRoundProductTypeFactory(
    factory.django.DjangoModelFactory[BiddingRoundProductType]
):
    class Meta:
        model = BiddingRoundProductType

    round = factory.SubFactory(BiddingRoundFactory)
    product_type = factory.SubFactory(ProductTypeFactory)
    target_amount_per_year = Decimal("1000.00")


class BiddingRoundProductPriceFactory(
    factory.django.DjangoModelFactory[BiddingRoundProductPrice]
):
    class Meta:
        model = BiddingRoundProductPrice

    round_product_type = factory.SubFactory(BiddingRoundProductTypeFactory)
    product = factory.LazyAttribute(
        lambda price: ProductFactory.create(type=price.round_product_type.product_type)
    )
    reference_value = Decimal("90.00")
    min_amount = Decimal("70.00")
    size = Decimal("1.0000")


class BidFactory(factory.django.DjangoModelFactory[Bid]):
    class Meta:
        model = Bid

    round = factory.SubFactory(BiddingRoundFactory)
    member = factory.SubFactory(MemberFactory)


class BidItemFactory(factory.django.DjangoModelFactory[BidItem]):
    class Meta:
        model = BidItem

    bid = factory.SubFactory(BidFactory)
    round_product_type = factory.SubFactory(BiddingRoundProductTypeFactory)
    product = factory.LazyAttribute(
        lambda bid_item: ProductFactory.create(
            type=bid_item.round_product_type.product_type
        )
    )
    quantity = 1
    amount_1 = Decimal("70.00")
