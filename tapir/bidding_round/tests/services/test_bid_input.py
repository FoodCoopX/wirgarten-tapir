from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tapir.bidding_round.services.bid_input import BidInput
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBidInput(TapirIntegrationTest):
    def test_fromMapping_default_convertsStringsToTypedValues(self):
        bid_input = BidInput.from_mapping(
            {"product_id": "product-1", "quantity": "2", "amount_1": "80,50"}
        )

        self.assertEqual(
            BidInput(
                product_id="product-1",
                quantity=2,
                amount_1=Decimal("80.50"),
            ),
            bid_input,
        )

    def test_fromMapping_withoutQuantity_defaultsToOneShare(self):
        bid_input = BidInput.from_mapping({"product_id": "product-1", "amount_1": "80"})

        self.assertEqual(1, bid_input.quantity)

    def test_fromMapping_withoutAmounts_leavesThemEmpty(self):
        bid_input = BidInput.from_mapping({"product_id": "product-1", "quantity": 1})

        self.assertIsNone(bid_input.amount_1)
        self.assertIsNone(bid_input.amount_2)
        self.assertIsNone(bid_input.amount_3)

    def test_fromMapping_bidRange_parsesBothAmounts(self):
        bid_input = BidInput.from_mapping(
            {
                "product_id": "product-1",
                "quantity": 1,
                "amount_1": "70",
                "amount_2": "90",
            }
        )

        self.assertEqual(Decimal("70"), bid_input.amount_1)
        self.assertEqual(Decimal("90"), bid_input.amount_2)
        self.assertIsNone(bid_input.amount_3)

    def test_fromMapping_nonNumericAmount_raisesValidationError(self):
        with pytest.raises(ValidationError):
            BidInput.from_mapping(
                {"product_id": "product-1", "quantity": 1, "amount_1": "viel"}
            )

    def test_fromMapping_nonIntegerQuantity_raisesValidationError(self):
        with pytest.raises(ValidationError):
            BidInput.from_mapping(
                {"product_id": "product-1", "quantity": "zwei", "amount_1": "80"}
            )
