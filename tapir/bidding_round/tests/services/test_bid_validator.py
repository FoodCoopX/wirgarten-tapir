import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
)
from tapir.bidding_round.services.bid_validator import BidValidator
from tapir.bidding_round.tests.factories import (
    BidItemFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBidValidator(TapirIntegrationTest):
    def _create_active_round_with_price(
        self, bid_levels=1, bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE
    ):
        price = BiddingRoundProductPriceFactory.create(
            reference_value=Decimal("90.00"), min_amount=Decimal("70.00")
        )
        bidding_round = price.round_product_type.round
        bidding_round.status = BIDDING_ROUND_STATUS_ACTIVE
        bidding_round.bidding_procedure = bidding_procedure
        bidding_round.bid_levels = bid_levels
        bidding_round.start_at = get_now(cache={}) - datetime.timedelta(hours=1)
        bidding_round.end_at = get_now(cache={}) + datetime.timedelta(days=1)
        bidding_round.save()
        return price.round_product_type, price.product

    def test_validate_givenValidAmount_accepts(self):
        round_product_type, product = self._create_active_round_with_price()

        BidValidator.validate(
            round_product_type.round,
            [
                {
                    "round_product_type_id": round_product_type.id,
                    "product_id": product.id,
                    "amount_1": "80.00",
                }
            ],
            cache={},
        )

    def test_validate_givenAmountBelowMinimum_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "60.00",
                    }
                ],
                cache={},
            )

    def test_validate_givenNegativeAmount_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "-1.00",
                    }
                ],
                cache={},
            )

    def test_validate_givenZeroAmount_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "0.00",
                    }
                ],
                cache={},
            )

    def test_validate_givenNonNumericAmount_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "viel",
                    }
                ],
                cache={},
            )

    def test_validate_givenProductOfAnotherRound_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()
        other_item = BidItemFactory.create()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": other_item.product_id,
                        "amount_1": "80.00",
                    }
                ],
                cache={},
            )

    def test_validate_withQuantity_accepts(self):
        round_product_type, product = self._create_active_round_with_price()

        BidValidator.validate(
            round_product_type.round,
            [
                {
                    "round_product_type_id": round_product_type.id,
                    "product_id": product.id,
                    "quantity": 3,
                    "amount_1": "80.00",
                }
            ],
            cache={},
        )

    def test_validate_withQuantityZero_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "quantity": 0,
                        "amount_1": "80.00",
                    }
                ],
                cache={},
            )

    def test_validate_withQuantityAboveMaximum_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "quantity": 6,
                        "amount_1": "80.00",
                    }
                ],
                cache={},
            )

    def test_validate_withNonIntegerQuantity_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "quantity": "zwei",
                        "amount_1": "80.00",
                    }
                ],
                cache={},
            )

    def test_validate_givenInactiveRound_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()
        bidding_round = round_product_type.round
        bidding_round.status = BIDDING_ROUND_STATUS_CLOSED
        bidding_round.save()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "80.00",
                    }
                ],
                cache={},
            )

    def test_validate_simple_givenSecondAmount_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "80.00",
                        "amount_2": "90.00",
                    }
                ],
                cache={},
            )

    def test_validate_bidRange_givenBothAmounts_accepts(self):
        round_product_type, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        BidValidator.validate(
            round_product_type.round,
            [
                {
                    "round_product_type_id": round_product_type.id,
                    "product_id": product.id,
                    "amount_1": "70.00",
                    "amount_2": "90.00",
                }
            ],
            cache={},
        )

    def test_validate_bidRange_withoutRed_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "70.00",
                    }
                ],
                cache={},
            )

    def test_validate_bidRange_withThirdAmount_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "70.00",
                        "amount_2": "90.00",
                        "amount_3": "100.00",
                    }
                ],
                cache={},
            )

    def test_validate_bidRange_givenDescendingAmounts_raisesValidationError(self):
        round_product_type, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        with pytest.raises(ValidationError):
            BidValidator.validate(
                round_product_type.round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "amount_1": "90.00",
                        "amount_2": "80.00",
                    }
                ],
                cache={},
            )

    def test_validate_bidRange_withQuantity_accepts(self):
        round_product_type, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        BidValidator.validate(
            round_product_type.round,
            [
                {
                    "round_product_type_id": round_product_type.id,
                    "product_id": product.id,
                    "quantity": 2,
                    "amount_1": "70.00",
                    "amount_2": "90.00",
                }
            ],
            cache={},
        )
