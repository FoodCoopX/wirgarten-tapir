from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestAverageBidLock(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _prepare_round(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00"), capacity=10
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )
        return round_

    def test_lockAverageBid_storesPositionSurchargeAndAmounts(self):
        round_ = self._prepare_round()

        BiddingRoundService.lock_average_bid(
            bidding_round=round_,
            position=70,
            surcharge_percent=10,
            surcharge_on_bids=True,
            surcharge_on_average=True,
            cache={},
        )

        round_.refresh_from_db()
        self.assertIsNotNone(round_.average_bid_locked_at)
        self.assertEqual(Decimal("70.00"), round_.locked_traffic_light_position)
        self.assertEqual(Decimal("10.00"), round_.locked_surcharge_percent)
        self.assertTrue(round_.locked_surcharge_on_bids)
        self.assertTrue(round_.locked_surcharge_on_average)
        self.assertIsNotNone(round_.locked_average_bid_per_share_per_month)
        self.assertIsNotNone(round_.locked_average_bid_per_share_per_year)
        self.assertIsNotNone(round_.locked_bidder_average_per_share_per_month)
        self.assertIsNotNone(round_.locked_bidder_average_per_share_per_year)

    def test_lockAverageBid_alreadyLocked_raisesValidationError(self):
        round_ = self._prepare_round()
        BiddingRoundService.lock_average_bid(round_, 50, 0, False, False, cache={})

        with self.assertRaises(ValidationError):
            BiddingRoundService.lock_average_bid(round_, 60, 0, False, False, cache={})

    def test_lockAverageBid_surchargeOutOfRange_raisesValidationError(self):
        round_ = self._prepare_round()

        with self.assertRaises(ValidationError):
            BiddingRoundService.lock_average_bid(
                round_, 50, 150, False, False, cache={}
            )

    def test_unlockAverageBid_clearsLock(self):
        round_ = self._prepare_round()
        BiddingRoundService.lock_average_bid(round_, 50, 5, True, True, cache={})

        BiddingRoundService.unlock_average_bid(round_, cache={})

        round_.refresh_from_db()
        self.assertIsNone(round_.average_bid_locked_at)
        self.assertIsNone(round_.locked_traffic_light_position)
        self.assertIsNone(round_.locked_average_bid_per_share_per_month)
        self.assertIsNone(round_.locked_bidder_average_per_share_per_month)
        self.assertEqual(Decimal("0"), round_.locked_surcharge_percent)
        self.assertFalse(round_.locked_surcharge_on_bids)
        self.assertFalse(round_.locked_surcharge_on_average)

    def test_unlockAverageBid_contractsCreated_raisesValidationError(self):
        round_ = self._prepare_round()
        BiddingRoundService.lock_average_bid(round_, 50, 0, False, False, cache={})
        round_.contracts_created_at = get_now()
        round_.save()

        with self.assertRaises(ValidationError):
            BiddingRoundService.unlock_average_bid(round_, cache={})
