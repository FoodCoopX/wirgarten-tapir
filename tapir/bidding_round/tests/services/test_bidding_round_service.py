import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tapir.bidding_round.config import ACTIVE, CLOSED, CONFIGURATION
from tapir.bidding_round.models import BiddingRoundProduct, BiddingRoundProductPrice
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BiddingRoundFactory,
    BiddingRoundProductFactory,
)
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBiddingRoundService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_createRound_createsConfigurationRound(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name="Beitragsrunde Test",
            bidding_procedure="simple",
            end_at=datetime.datetime.combine(
                growing_period.start_date,
                datetime.time(hour=23, minute=59),
                tzinfo=datetime.timezone.utc,
            ),
            product_type_id=product_type.id,
            cache={},
        )
        self.assertEqual(CONFIGURATION, bidding_round.status)
        self.assertEqual("Beitragsrunde Test", bidding_round.name)
        self.assertEqual(growing_period, bidding_round.growing_period)

    def test_createRound_withoutEndDate_raisesValidationError(self):
        with pytest.raises(ValidationError):
            BiddingRoundService.create_round(
                growing_period=GrowingPeriodFactory.create(),
                name="Beitragsrunde Test",
                bidding_procedure="simple",
                end_at=None,
                cache={},
            )

    def test_createRound_withProductTypeId_createsBiddingRoundProduct(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name="Beitragsrunde Test",
            bidding_procedure="simple",
            end_at=datetime.datetime.combine(
                growing_period.start_date,
                datetime.time(hour=23, minute=59),
                tzinfo=datetime.timezone.utc,
            ),
            product_type_id=product_type.id,
            cache={},
        )
        self.assertEqual(
            [product_type.id],
            list(
                BiddingRoundProduct.objects.filter(round=bidding_round).values_list(
                    "product_type_id", flat=True
                )
            ),
        )

    def test_createRound_withoutProductTypeId_defaultsToTheOnlyProductType(self):
        growing_period = GrowingPeriodFactory.create()
        capacity = ProductCapacityFactory.create(period=growing_period)
        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name="Beitragsrunde Test",
            bidding_procedure="simple",
            end_at=datetime.datetime.combine(
                growing_period.start_date,
                datetime.time(hour=23, minute=59),
                tzinfo=datetime.timezone.utc,
            ),
            cache={},
        )
        self.assertEqual(
            [capacity.product_type_id],
            list(
                BiddingRoundProduct.objects.filter(round=bidding_round).values_list(
                    "product_type_id", flat=True
                )
            ),
        )

    def test_createRound_withoutProductTypeIdAndMultipleCapacities_raisesValidationError(
        self,
    ):
        growing_period = GrowingPeriodFactory.create()
        ProductCapacityFactory.create(period=growing_period)
        ProductCapacityFactory.create(period=growing_period)
        with pytest.raises(ValidationError):
            BiddingRoundService.create_round(
                growing_period=growing_period,
                name="Beitragsrunde Test",
                bidding_procedure="simple",
                end_at=datetime.datetime.combine(
                    growing_period.start_date,
                    datetime.time(hour=23, minute=59),
                    tzinfo=datetime.timezone.utc,
                ),
                cache={},
            )

    def test_createRound_withValues_storesValues(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        product = ProductFactory.create(type=product_type)
        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name="Beitragsrunde Test",
            bidding_procedure="simple",
            end_at=datetime.datetime.combine(
                growing_period.start_date,
                datetime.time(hour=23, minute=59),
                tzinfo=datetime.timezone.utc,
            ),
            product_type_id=product_type.id,
            target_amount_per_year="1000.00",
            prices=[
                {
                    "product_id": product.id,
                    "reference_value": "80.00",
                    "min_amount": "60.00",
                }
            ],
            cache={},
        )
        round_product = bidding_round.products.get()
        self.assertEqual(Decimal("1000.00"), round_product.target_amount_per_year)
        price = BiddingRoundProductPrice.objects.get(
            round_product=round_product, product=product
        )
        self.assertEqual(Decimal("80.00"), price.reference_value)
        self.assertEqual(Decimal("60.00"), price.min_amount)

    def test_updateRoundConfig_updatesValuesAndRemovesStalePrices(self):
        bidding_round = BiddingRoundFactory.create()
        round_product = BiddingRoundProductFactory.create(round=bidding_round)
        product_1 = ProductFactory.create(type=round_product.product_type)
        product_2 = ProductFactory.create(type=round_product.product_type)
        BiddingRoundProductPrice.objects.create(
            round_product=round_product,
            product=product_2,
            reference_value=Decimal("50.00"),
        )

        BiddingRoundService.update_round_config(
            bidding_round,
            {
                "target_amount_per_year": "1000.00",
                "prices": [
                    {
                        "product_id": product_1.id,
                        "reference_value": "80.00",
                        "min_amount": "60.00",
                    }
                ],
            },
            cache={},
        )

        round_product.refresh_from_db()
        self.assertEqual(Decimal("1000.00"), round_product.target_amount_per_year)
        self.assertEqual(
            {product_1.id},
            set(
                BiddingRoundProductPrice.objects.filter(
                    round_product=round_product
                ).values_list("product_id", flat=True)
            ),
        )

    def test_updateRoundConfig_minAmountAboveReference_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create()
        round_product = BiddingRoundProductFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product.product_type)
        with pytest.raises(ValidationError):
            BiddingRoundService.update_round_config(
                bidding_round,
                {
                    "prices": [
                        {
                            "product_id": product.id,
                            "reference_value": "50.00",
                            "min_amount": "80.00",
                        }
                    ]
                },
                cache={},
            )

    def _create_round_with_target(self, **kwargs):
        bidding_round = BiddingRoundFactory.create(**kwargs)
        round_product = BiddingRoundProductFactory.create(round=bidding_round)
        round_product.target_amount_per_year = Decimal("1000.00")
        round_product.save()
        return bidding_round

    def test_startRound_transitionsToActive(self):
        bidding_round = self._create_round_with_target()
        BiddingRoundService.start_round(bidding_round, cache={})
        self.assertEqual(ACTIVE, bidding_round.status)

    def test_startRound_withoutTargetAmount_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductFactory.create(round=bidding_round)
        with pytest.raises(ValidationError):
            BiddingRoundService.start_round(bidding_round, cache={})

    def test_startRound_notInConfiguration_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(status=ACTIVE)
        with pytest.raises(ValidationError):
            BiddingRoundService.start_round(bidding_round, cache={})

    def test_startRound_withAnotherActiveRound_raisesValidationError(self):
        BiddingRoundFactory.create(status=ACTIVE)
        bidding_round = self._create_round_with_target()
        with pytest.raises(ValidationError):
            BiddingRoundService.start_round(bidding_round, cache={})

    def test_startRound_afterOtherRoundClosed_succeeds(self):
        other_active = BiddingRoundFactory.create(status=ACTIVE)
        BiddingRoundService.close_round(other_active, cache={})
        bidding_round = self._create_round_with_target()
        BiddingRoundService.start_round(bidding_round, cache={})
        self.assertEqual(ACTIVE, bidding_round.status)

    def test_closeRound_transitionsToClosed(self):
        bidding_round = BiddingRoundFactory.create(status=ACTIVE)
        BiddingRoundService.close_round(bidding_round, cache={})
        self.assertEqual(CLOSED, bidding_round.status)

    def test_reopenRound_transitionsToActive(self):
        bidding_round = BiddingRoundFactory.create(status=CLOSED)
        BiddingRoundService.reopen_round(bidding_round, cache={})
        self.assertEqual(ACTIVE, bidding_round.status)

    def test_reopenRound_notClosed_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(status=CONFIGURATION)
        with pytest.raises(ValidationError):
            BiddingRoundService.reopen_round(bidding_round, cache={})

    def test_reopenRound_withAnotherActiveRound_raisesValidationError(self):
        BiddingRoundFactory.create(status=ACTIVE)
        bidding_round = BiddingRoundFactory.create(status=CLOSED)
        with pytest.raises(ValidationError):
            BiddingRoundService.reopen_round(bidding_round, cache={})

    def test_reopenRound_afterOtherRoundClosed_succeeds(self):
        other_active = BiddingRoundFactory.create(status=ACTIVE)
        BiddingRoundService.close_round(other_active, cache={})
        bidding_round = BiddingRoundFactory.create(status=CLOSED)
        BiddingRoundService.reopen_round(bidding_round, cache={})
        self.assertEqual(ACTIVE, bidding_round.status)

    def test_reopenRound_contractsCreated_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(
            status=CLOSED, contracts_created_at=get_now()
        )
        with pytest.raises(ValidationError):
            BiddingRoundService.reopen_round(bidding_round, cache={})

    def test_deleteRound_contractsCreated_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(
            status=CLOSED, contracts_created_at=get_now()
        )
        with pytest.raises(ValidationError):
            BiddingRoundService.delete_round(bidding_round, cache={})

    def test_saveAdminBid_afterContractsCreated_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(
            status=CLOSED, contracts_created_at=get_now()
        )
        round_product = BiddingRoundProductFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()

        with pytest.raises(ValidationError):
            BiddingRoundService.save_admin_bid(
                bidding_round,
                member,
                cache={},
                items=[
                    {
                        "round_product_id": round_product.id,
                        "product_id": product.id,
                        "quantity": 1,
                        "amount_1": "80.00",
                    }
                ],
            )

    def test_saveAdminBid_pickupChangeAfterContracts_raisesValidationError(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        bidding_round = BiddingRoundFactory.create(
            status=CLOSED, contracts_created_at=get_now()
        )
        member = MemberFactory.create()
        BidFactory.create(round=bidding_round, member=member)
        pickup_location = PickupLocationFactory.create()

        with pytest.raises(ValidationError):
            BiddingRoundService.save_admin_bid(
                bidding_round,
                member,
                cache={},
                pickup_location_id=pickup_location.id,
            )

    def test_getCurrentOpenRound_returnsEarliestActiveWithFutureEndDate(self):
        earlier_round = BiddingRoundFactory.create(
            status=ACTIVE, end_at=get_now() + datetime.timedelta(days=10)
        )
        BiddingRoundFactory.create(
            status=ACTIVE, end_at=get_now() + datetime.timedelta(days=20)
        )
        self.assertEqual(
            earlier_round, BiddingRoundService.get_current_open_round(cache={})
        )

    def test_getCurrentOpenRound_onlyExpiredOrClosed_returnsNone(self):
        BiddingRoundFactory.create(
            status=ACTIVE, end_at=get_now() - datetime.timedelta(days=1)
        )
        BiddingRoundFactory.create(
            status=CLOSED, end_at=get_now() + datetime.timedelta(days=10)
        )
        self.assertIsNone(BiddingRoundService.get_current_open_round(cache={}))

    def test_getBiddableProductTypesForRound_returnsActiveTypesOfTargetPeriod(
        self,
    ):
        bidding_round = BiddingRoundFactory.create()
        capacity = ProductCapacityFactory.create(period=bidding_round.growing_period)
        ProductCapacityFactory.create(period=GrowingPeriodFactory.create())

        biddable = BiddingRoundService.get_biddable_product_types_for_round(
            bidding_round, cache={}
        )

        self.assertIn(capacity.product_type, biddable)
        self.assertEqual(1, len(biddable))

    def test_getOrCreateBid_existingBid_returnsSameBid(self):
        bid = BidFactory.create()
        result = BiddingRoundService.get_or_create_bid(bid.member, bid.round, cache={})
        self.assertEqual(bid, result)
        self.assertEqual(1, bid.round.bids.count())

    def test_getOrCreateBid_newMember_createsBid(self):
        member = MemberFactory.create()
        bidding_round = BiddingRoundFactory.create()
        bid = BiddingRoundService.get_or_create_bid(member, bidding_round, cache={})
        self.assertEqual(member, bid.member)
        self.assertEqual(bidding_round, bid.round)

    def test_isPickupLocationsEnabled_respectsParameter(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        self.assertTrue(BiddingRoundService.is_pickup_location_change_enabled(cache={}))

        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="false")
        self.assertFalse(
            BiddingRoundService.is_pickup_location_change_enabled(cache={})
        )
