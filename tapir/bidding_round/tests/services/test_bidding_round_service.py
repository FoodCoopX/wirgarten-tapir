import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tapir.bidding_round.config import (
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
    BIDDING_ROUND_STATUS_CONFIGURATION,
)
from tapir.bidding_round.models import Bid, BiddingRound
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
    BiddingRoundProductTypeFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBiddingRoundService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @staticmethod
    def _end_at(growing_period):
        return datetime.datetime.combine(
            growing_period.start_date,
            datetime.time(hour=23, minute=59),
            tzinfo=datetime.timezone.utc,
        )

    @staticmethod
    def _add_round_price(bidding_round):
        round_product_type = bidding_round.product_types.first()
        product = ProductFactory.create(type=round_product_type.product_type)
        return BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
        )

    def test_createRound_createsConfigurationRoundWithProductType(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()

        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name="Beitragsrunde Test",
            end_at=self._end_at(growing_period),
            product_type_id=product_type.id,
            target_amount_per_year="1000.00",
            cache={},
        )

        self.assertEqual(BIDDING_ROUND_STATUS_CONFIGURATION, bidding_round.status)
        self.assertEqual(growing_period, bidding_round.growing_period)
        round_product_type = bidding_round.product_types.get()
        self.assertEqual(product_type, round_product_type.product_type)
        self.assertEqual(Decimal("1000.00"), round_product_type.target_amount_per_year)

    def test_createRound_withoutEndDate_raisesValidationError(self):
        with pytest.raises(ValidationError):
            BiddingRoundService.create_round(
                growing_period=GrowingPeriodFactory.create(),
                name="Beitragsrunde Test",
                end_at=None,
                cache={},
            )

    def test_startRound_withoutTargetAmount_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=None
        )
        self._add_round_price(bidding_round)

        with pytest.raises(ValidationError):
            BiddingRoundService.start_round(bidding_round, cache={})

    def test_startRound_withoutPrices_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)

        with pytest.raises(ValidationError):
            BiddingRoundService.start_round(bidding_round, cache={})

    def test_startRound_setsStatusActive(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)
        self._add_round_price(bidding_round)

        BiddingRoundService.start_round(bidding_round, cache={})
        bidding_round.refresh_from_db()

        self.assertEqual(BIDDING_ROUND_STATUS_ACTIVE, bidding_round.status)

    def test_startRound_whenAnotherRoundIsActive_raisesValidationError(self):
        BiddingRoundFactory.create(status=BIDDING_ROUND_STATUS_ACTIVE)
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)
        self._add_round_price(bidding_round)

        with pytest.raises(ValidationError):
            BiddingRoundService.start_round(bidding_round, cache={})

    def test_closeRound_setsStatusClosed(self):
        bidding_round = BiddingRoundFactory.create(status=BIDDING_ROUND_STATUS_ACTIVE)

        BiddingRoundService.close_round(bidding_round, cache={})
        bidding_round.refresh_from_db()

        self.assertEqual(BIDDING_ROUND_STATUS_CLOSED, bidding_round.status)

    def test_reopenRound_afterContractsWereCreated_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(
            status=BIDDING_ROUND_STATUS_CLOSED, contracts_created_at=get_now(cache={})
        )

        with pytest.raises(ValidationError):
            BiddingRoundService.reopen_round(bidding_round, cache={})

    def test_deleteRound_withStatusActive_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(status=BIDDING_ROUND_STATUS_ACTIVE)

        with pytest.raises(ValidationError):
            BiddingRoundService.delete_round(bidding_round, cache={})

    def test_createRound_withoutPrices_raisesValidationError(self):
        growing_period = GrowingPeriodFactory.create()

        with pytest.raises(ValidationError):
            BiddingRoundService.create_round(
                growing_period=growing_period,
                name="Beitragsrunde Test",
                end_at=self._end_at(growing_period),
                product_type_id=ProductTypeFactory.create().id,
                prices=[],
                cache={},
            )

        self.assertFalse(BiddingRound.objects.exists())

    def test_getCurrentOpenRound_startInTheFuture_returnsNone(self):
        now = get_now(cache={})
        BiddingRoundFactory.create(
            status=BIDDING_ROUND_STATUS_ACTIVE,
            start_at=now + datetime.timedelta(days=1),
            end_at=now + datetime.timedelta(days=2),
        )

        self.assertIsNone(BiddingRoundService.get_current_open_round(cache={}))

    def test_updateRoundConfig_givenBidsExistAndSensitiveChange_raisesValidationError(
        self,
    ):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)
        BidFactory.create(round=bidding_round)

        with pytest.raises(ValidationError):
            BiddingRoundService.update_round_config(
                bidding_round, {"target_amount_per_year": "2000.00"}, cache={}
            )

    def test_updateRoundConfig_givenBidsExistAndUnchangedSensitiveValues_updatesName(
        self,
    ):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        price = self._add_round_price(bidding_round)
        BidFactory.create(round=bidding_round)

        BiddingRoundService.update_round_config(
            bidding_round,
            {
                "name": "Neuer Name",
                "product_type_id": round_product_type.product_type_id,
                "target_amount_per_year": str(
                    round_product_type.target_amount_per_year
                ),
                "prices": [
                    {
                        "product_id": price.product_id,
                        "reference_value": str(price.reference_value),
                        "min_amount": str(price.min_amount),
                        "size": str(price.size),
                    }
                ],
            },
            cache={},
        )

        bidding_round.refresh_from_db()
        self.assertEqual("Neuer Name", bidding_round.name)

    def test_updateRoundConfig_startAfterEnd_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)

        with pytest.raises(ValidationError):
            BiddingRoundService.update_round_config(
                bidding_round,
                {"start_at": bidding_round.end_at + datetime.timedelta(days=1)},
                cache={},
            )

    def test_updateRoundConfig_afterContractsWereCreated_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(
            contracts_created_at=get_now(cache={})
        )
        BiddingRoundProductTypeFactory.create(round=bidding_round)

        with pytest.raises(ValidationError):
            BiddingRoundService.update_round_config(
                bidding_round, {"name": "Neuer Name"}, cache={}
            )

    def test_saveBid_createsBidWithOneItem(self):
        bidding_round, round_product_type, product = self._create_active_round()
        member = MemberFactory.create()

        BiddingRoundService.save_bid(
            member,
            bidding_round,
            [
                {
                    "round_product_type_id": round_product_type.id,
                    "product_id": product.id,
                    "amount_1": "85.00",
                }
            ],
            cache={},
        )

        bid = Bid.objects.get(round=bidding_round, member=member)
        self.assertEqual(1, bid.items.count())
        self.assertEqual(Decimal("85.00"), bid.items.get().amount_1)

    def test_saveBid_calledTwice_updatesTheSameBid(self):
        bidding_round, round_product_type, product = self._create_active_round()
        member = MemberFactory.create()
        items = [
            {
                "round_product_type_id": round_product_type.id,
                "product_id": product.id,
                "amount_1": "85.00",
            }
        ]

        BiddingRoundService.save_bid(member, bidding_round, items, cache={})
        items[0]["amount_1"] = "95.00"
        BiddingRoundService.save_bid(member, bidding_round, items, cache={})

        self.assertEqual(1, Bid.objects.filter(round=bidding_round).count())
        self.assertEqual(
            Decimal("95.00"), Bid.objects.get(round=bidding_round).items.get().amount_1
        )

    def _create_active_round(self):
        bidding_round = BiddingRoundFactory.create(
            status=BIDDING_ROUND_STATUS_ACTIVE,
            start_at=get_now(cache={}) - datetime.timedelta(hours=1),
            end_at=get_now(cache={}) + datetime.timedelta(days=1),
            growing_period=GrowingPeriodFactory.create(),
        )
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
            reference_value=Decimal("90.00"),
            min_amount=Decimal("70.00"),
        )
        return bidding_round, round_product_type, product
