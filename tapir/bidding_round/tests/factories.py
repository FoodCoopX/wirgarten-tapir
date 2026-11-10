import datetime
from decimal import Decimal

import factory

from tapir.bidding_round.config import CONFIGURATION, SIMPLE
from tapir.bidding_round.models import (
    Bid,
    BidItem,
    BiddingRound,
    BiddingRoundProduct,
    BiddingRoundProductPrice,
)
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    ProductTypeFactory,
)

NOW = datetime.datetime(2023, 3, 15, 12, 0, tzinfo=datetime.timezone.utc)
TODAY = NOW.date()


class BiddingRoundFactory(factory.django.DjangoModelFactory[BiddingRound]):
    class Meta:
        model = BiddingRound

    growing_period = factory.SubFactory(GrowingPeriodFactory)
    name = factory.Faker("sentence", nb_words=2)
    status = CONFIGURATION
    bidding_procedure = SIMPLE
    end_at = factory.LazyAttribute(
        lambda bidding_round: datetime.datetime.combine(
            bidding_round.growing_period.start_date,
            datetime.time(hour=23, minute=59),
            tzinfo=datetime.timezone.utc,
        )
    )
    include_auto_renewed = True


class BiddingRoundProductFactory(
    factory.django.DjangoModelFactory[BiddingRoundProduct]
):
    class Meta:
        model = BiddingRoundProduct

    round = factory.SubFactory(BiddingRoundFactory)
    product_type = factory.SubFactory(ProductTypeFactory)


class BiddingRoundProductPriceFactory(
    factory.django.DjangoModelFactory[BiddingRoundProductPrice]
):
    class Meta:
        model = BiddingRoundProductPrice

    round_product = factory.SubFactory(BiddingRoundProductFactory)
    product = factory.LazyAttribute(
        lambda price: ProductFactory.create(type=price.round_product.product_type)
    )
    reference_value = Decimal("90.00")
    min_amount = Decimal("70.00")


class BidFactory(factory.django.DjangoModelFactory[Bid]):
    class Meta:
        model = Bid

    round = factory.SubFactory(BiddingRoundFactory)
    member = factory.SubFactory(MemberFactory)
    pickup_location = None
    entered_by_admin = False
    admin_confirmed = None


class BidItemFactory(factory.django.DjangoModelFactory[BidItem]):
    class Meta:
        model = BidItem

    bid = factory.SubFactory(BidFactory)
    round_product = factory.SubFactory(BiddingRoundProductFactory)
    product = factory.LazyAttribute(
        lambda bid_item: ProductFactory.create(type=bid_item.round_product.product_type)
    )
    quantity = 1
    amount_1 = Decimal("70.00")
    amount_2 = Decimal("80.00")
    amount_3 = Decimal("90.00")
