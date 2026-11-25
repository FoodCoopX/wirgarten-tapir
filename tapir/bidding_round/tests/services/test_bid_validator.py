import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
)
from tapir.bidding_round.services.bid_input import BidInput
from tapir.bidding_round.services.bid_validator import BidValidator
from tapir.bidding_round.tests.factories import (
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBidValidator(TapirIntegrationTest):
    def _create_active_round_with_price(
        self,
        bid_levels=1,
        bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE,
    ):
        bidding_round = BiddingRoundFactory.create(
            status=BIDDING_ROUND_STATUS_ACTIVE,
            bidding_procedure=bidding_procedure,
            bid_levels=bid_levels,
            start_at=get_now(cache={}) - datetime.timedelta(hours=1),
            end_at=get_now(cache={}) + datetime.timedelta(days=1),
        )
        product = ProductFactory.create(type=bidding_round.product_type)
        BiddingRoundProductPriceFactory.create(
            round=bidding_round,
            product=product,
            reference_value=Decimal("90.00"),
            min_amount=Decimal("70.00"),
        )
        return bidding_round, product

    def test_validate_default_returnsTheValidatedInput(self):
        bidding_round, product = self._create_active_round_with_price()
        bid_input = BidInput(
            product_id=product.id, quantity=2, amount_1=Decimal("80.00")
        )

        validated = BidValidator.validate(bidding_round, bid_input, cache={})

        self.assertEqual(bid_input, validated)

    def test_validate_amountBelowMinimum_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(product_id=product.id, quantity=1, amount_1=Decimal("60.00")),
                cache={},
            )

    def test_validate_negativeAmount_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(product_id=product.id, quantity=1, amount_1=Decimal("-1.00")),
                cache={},
            )

    def test_validate_zeroAmount_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(product_id=product.id, quantity=1, amount_1=Decimal("0.00")),
                cache={},
            )

    def test_validate_productOfAnotherRound_raisesValidationError(self):
        bidding_round, _product = self._create_active_round_with_price()
        other_product = ProductFactory.create()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(
                    product_id=other_product.id,
                    quantity=1,
                    amount_1=Decimal("80.00"),
                ),
                cache={},
            )

    def test_validate_productWithoutPriceRow_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(
            status=BIDDING_ROUND_STATUS_ACTIVE,
            start_at=get_now(cache={}) - datetime.timedelta(hours=1),
            end_at=get_now(cache={}) + datetime.timedelta(days=1),
        )
        product = ProductFactory.create(type=bidding_round.product_type)

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(product_id=product.id, quantity=1, amount_1=Decimal("80.00")),
                cache={},
            )

    def test_validate_quantityAboveMaximum_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(product_id=product.id, quantity=6, amount_1=Decimal("80.00")),
                cache={},
            )

    def test_validate_quantityZero_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(product_id=product.id, quantity=0, amount_1=Decimal("80.00")),
                cache={},
            )

    def test_validate_inactiveRound_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price()
        bidding_round.status = BIDDING_ROUND_STATUS_CLOSED
        bidding_round.save()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(product_id=product.id, quantity=1, amount_1=Decimal("80.00")),
                cache={},
            )

    def test_validate_roundNotStarted_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price()
        bidding_round.start_at = get_now(cache={}) + datetime.timedelta(days=1)
        bidding_round.save()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(product_id=product.id, quantity=1, amount_1=Decimal("80.00")),
                cache={},
            )

    def test_validate_simple_givenSecondAmount_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price()

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(
                    product_id=product.id,
                    quantity=1,
                    amount_1=Decimal("80.00"),
                    amount_2=Decimal("90.00"),
                ),
                cache={},
            )

    def test_validate_bidRange_givenBothAmounts_accepts(self):
        bidding_round, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        validated = BidValidator.validate(
            bidding_round,
            BidInput(
                product_id=product.id,
                quantity=1,
                amount_1=Decimal("70.00"),
                amount_2=Decimal("90.00"),
            ),
            cache={},
        )

        self.assertEqual(Decimal("70.00"), validated.amount_1)
        self.assertEqual(Decimal("90.00"), validated.amount_2)
        self.assertIsNone(validated.amount_3)

    def test_validate_bidRange_withoutRed_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(
                    product_id=product.id,
                    quantity=1,
                    amount_1=Decimal("70.00"),
                ),
                cache={},
            )

    def test_validate_bidRange_withThirdAmount_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(
                    product_id=product.id,
                    quantity=1,
                    amount_1=Decimal("70.00"),
                    amount_2=Decimal("90.00"),
                    amount_3=Decimal("100.00"),
                ),
                cache={},
            )

    def test_validate_bidRange_givenDescendingAmounts_raisesValidationError(self):
        bidding_round, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        with pytest.raises(ValidationError):
            BidValidator.validate(
                bidding_round,
                BidInput(
                    product_id=product.id,
                    quantity=1,
                    amount_1=Decimal("90.00"),
                    amount_2=Decimal("80.00"),
                ),
                cache={},
            )

    def test_validate_bidRange_withQuantity_accepts(self):
        bidding_round, product = self._create_active_round_with_price(
            bid_levels=2, bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )

        validated = BidValidator.validate(
            bidding_round,
            BidInput(
                product_id=product.id,
                quantity=2,
                amount_1=Decimal("70.00"),
                amount_2=Decimal("90.00"),
            ),
            cache={},
        )

        self.assertEqual(2, validated.quantity)
