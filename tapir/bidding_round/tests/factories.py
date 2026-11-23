import datetime
from decimal import Decimal

import factory
from django.utils import timezone

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CONFIGURATION
from tapir.bidding_round.models import (
    Bid,
    BiddingRound,
    BiddingRoundProductPrice,
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
    product_type = factory.SubFactory(ProductTypeFactory)
    target_amount_per_year = Decimal("1000.00")
    start_at = factory.LazyFunction(timezone.now)
    end_at = factory.LazyAttribute(
        lambda bidding_round: bidding_round.start_at + datetime.timedelta(days=30)
    )


class BiddingRoundProductPriceFactory(
    factory.django.DjangoModelFactory[BiddingRoundProductPrice]
):
    class Meta:
        model = BiddingRoundProductPrice

    round = factory.SubFactory(BiddingRoundFactory)
    product = factory.LazyAttribute(
        lambda price: ProductFactory.create(type=price.round.product_type)
    )
    reference_value = Decimal("90.00")
    min_amount = Decimal("70.00")
    size = Decimal("1.0000")


class BidFactory(factory.django.DjangoModelFactory[Bid]):
    class Meta:
        model = Bid

    round = factory.SubFactory(BiddingRoundFactory)
    member = factory.SubFactory(MemberFactory)
    product = factory.LazyAttribute(
        lambda bid: ProductFactory.create(type=bid.round.product_type)
    )
    quantity = 1
    amount_1 = Decimal("70.00")
