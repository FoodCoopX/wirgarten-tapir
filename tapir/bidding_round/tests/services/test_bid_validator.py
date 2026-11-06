import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tapir.accounts.models import TapirUser
from tapir.bidding_round.config import ACTIVE, TRAFFIC_LIGHT
from tapir.bidding_round.models import Bid, BidItem
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.tests.factories import (
    BiddingRoundFactory,
    BiddingRoundProductFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.bidding_round.tests.helpers import build_item, create_open_round
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBidValidator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_validate_amountBelowZero_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product, amount_1="-1.00")],
                cache={},
            )

    def test_validate_amountBelowMinAmountOfVariant_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product=round_product,
            product=product,
            reference_value=None,
            min_amount=Decimal("70.00"),
        )

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product, amount_1="60.00")],
                cache={},
            )

    def test_validate_amountAtMinAmountOfVariant_accepts(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product=round_product,
            product=product,
            reference_value=None,
            min_amount=Decimal("70.00"),
        )

        bid = BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="70.00")],
            cache={},
        )

        self.assertEqual(Decimal("70.00"), bid.items.get().amount_1)

    def test_validate_amountWithCommaSeparator_accepts(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        bid = BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="80,00")],
            cache={},
        )

        self.assertEqual(Decimal("80.00"), bid.items.get().amount_1)

    def test_validate_quantityNotAllowed_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product, quantity=99)],
                cache={},
            )

    def test_validate_productOfDifferentType_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create()

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product)],
                cache={},
            )

    def test_validate_expiredRound_rejects(self):
        expired_round = BiddingRoundFactory.create(
            status=ACTIVE,
            start_at=get_now() - datetime.timedelta(days=10),
            end_at=get_now() - datetime.timedelta(days=1),
        )
        round_product = BiddingRoundProductFactory.create(round=expired_round)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                expired_round,
                [build_item(round_product, product)],
                cache={},
            )

    def test_validate_roundNotStarted_rejects(self):
        future_round = BiddingRoundFactory.create(
            status=ACTIVE,
            start_at=get_now() + datetime.timedelta(days=1),
            end_at=get_now() + datetime.timedelta(days=10),
        )
        round_product = BiddingRoundProductFactory.create(round=future_round)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                future_round,
                [build_item(round_product, product)],
                cache={},
            )

    def test_validate_nonMember_denied(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        user = TapirUser(
            username="testuser", email="test@example.com", password="top_secret"
        )
        user.save()

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                user, round_, [build_item(round_product, product)], cache={}
            )

    def test_saveBid_upsertsBidAndItems(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()

        bid = BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="85.00")],
            cache={},
        )

        self.assertEqual(1, Bid.objects.filter(round=round_, member=member).count())
        self.assertEqual(1, BidItem.objects.filter(bid=bid).count())
        self.assertEqual(
            Decimal("85.00"),
            BidItem.objects.filter(bid=bid).get().amount_1,
        )

    def test_save_simpleRoundWithTwoLevels_storesAmounts(self):
        round_ = create_open_round(bid_levels=2)
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        bid = BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="70.00", amount_2="80.00")],
            cache={},
        )

        bid_item = bid.items.get()
        self.assertEqual(Decimal("70.00"), bid_item.amount_1)
        self.assertEqual(Decimal("80.00"), bid_item.amount_2)
        self.assertIsNone(bid_item.amount_3)

    def test_save_simpleRoundWithTwoLevels_missingSecondLevel_rejects(self):
        round_ = create_open_round(bid_levels=2)
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product, amount_1="70.00")],
                cache={},
            )

    def test_save_simpleRoundWithOneLevel_extraLevel_rejects(self):
        round_ = create_open_round(bid_levels=1)
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [
                    build_item(
                        round_product, product, amount_1="70.00", amount_2="80.00"
                    )
                ],
                cache={},
            )

    def test_save_levelsNotAscending_rejects(self):
        round_ = create_open_round(bid_levels=3)
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [
                    build_item(
                        round_product,
                        product,
                        amount_1="70.00",
                        amount_2="90.00",
                        amount_3="80.00",
                    )
                ],
                cache={},
            )

    def test_save_traffic_lightStoresGreenYellowRed(self):
        round_ = create_open_round(bidding_procedure=TRAFFIC_LIGHT)
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()

        bid = BiddingRoundService.save_bid(
            member,
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="70.00",
                    amount_2="80.00",
                    amount_3="90.00",
                )
            ],
            cache={},
        )

        bid_item = bid.items.get()
        self.assertEqual(Decimal("80.00"), bid_item.amount_2)
        self.assertEqual(Decimal("70.00"), bid_item.amount_1)
        self.assertEqual(Decimal("90.00"), bid_item.amount_3)

    def test_save_traffic_lightMissingYellow_rejects(self):
        round_ = create_open_round(bidding_procedure=TRAFFIC_LIGHT)
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product, amount_1="70.00")],
                cache={},
            )

    def test_validate_pickupLocationsEnabled_missingFirstChoice_rejects(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product)],
                cache={},
            )

    def test_validate_pickupLocationsEnabled_withFirstChoice_succeeds(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        pickup_location = PickupLocationFactory.create()

        bid = BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product)],
            pickup_location_id=pickup_location.id,
            cache={},
        )

        self.assertEqual(pickup_location, bid.pickup_location)

    def test_validate_pickupLocationsDisabled_pickupLocationIgnored(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="false")
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        bid = BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product)],
            cache={},
        )

        self.assertIsNone(bid.pickup_location)

    def test_validate_quantityDisabled_quantityTwo_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product, quantity=2)],
                cache={},
            )

    def test_validate_quantityEnabled_quantityTwo_accepts(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_BID_QUANTITY_ENABLED
        ).update(value="true")
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        bid = BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, quantity=2)],
            cache={},
        )

        self.assertEqual(2, bid.items.get().quantity)

    def test_validate_roundProductOfAnotherRound_rejects(self):
        round_ = create_open_round()
        other_round = create_open_round()
        other_round_product = BiddingRoundProductFactory.create(round=other_round)
        product = ProductFactory.create(type=other_round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(other_round_product, product)],
                cache={},
            )

    def test_validate_nonNumericAmount_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product, amount_1="not a number")],
                cache={},
            )

    def test_validate_nonFiniteAmount_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product, amount_1="NaN")],
                cache={},
            )

    def test_validate_unknownPickupLocation_rejects(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        with pytest.raises(ValidationError):
            BiddingRoundService.save_bid(
                MemberFactory.create(),
                round_,
                [build_item(round_product, product)],
                pickup_location_id="does-not-exist",
                cache={},
            )

    def test_validate_pickupLocationsDisabled_keepsMemberCurrentLocation(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="false")
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        own_location = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(member=member, pickup_location=own_location)
        other_location = PickupLocationFactory.create()

        bid = BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product)],
            pickup_location_id=other_location.id,
            cache={},
        )

        self.assertEqual(own_location, bid.pickup_location)
