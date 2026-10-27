import datetime
from decimal import Decimal
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from tapir.bidding_round.config import ACTIVE, CLOSED
from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductFactory,
)
from tapir.bidding_round.tests.helpers import create_round_product_with_product
from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.models import (
    GrowingPeriod,
    MemberPickupLocation,
    Subscription,
    WaitingListProductWish,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PickupLocationFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now, get_today


def create_closed_round(position=Decimal("50")):
    round_ = BiddingRoundFactory.create(
        status=CLOSED,
        end_at=get_now() - datetime.timedelta(days=1),
    )
    round_.average_bid_locked_at = get_now()
    round_.locked_traffic_light_position = position
    round_.locked_surcharge_percent = Decimal("0")
    round_.locked_average_bid_per_share_per_month = Decimal("0")
    round_.locked_average_bid_per_share_per_year = Decimal("0")
    round_.save()
    return round_


@patch.object(
    GlobalCapacityChecker,
    "get_product_type_ids_without_enough_capacity_for_order",
    autospec=True,
)
class TestContractCreator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _create_bid(
        self,
        round_,
        member=None,
        admin_confirmed=True,
        pickup_location=None,
        amount_1=Decimal("80.00"),
        amount_2=None,
        amount_3=None,
    ):
        member = member or MemberFactory.create()
        bid = BidFactory.create(
            round=round_,
            member=member,
            admin_confirmed=get_now() if admin_confirmed else None,
            pickup_location=pickup_location,
        )
        round_product = round_.products.first()
        if round_product is None:
            round_product = BiddingRoundProductFactory.create(round=round_)
        BidItemFactory.create(
            bid=bid,
            round_product=round_product,
            quantity=1,
            amount_1=amount_1,
            amount_2=amount_2,
            amount_3=amount_3,
        )
        ProductPriceFactory.create(
            product=bid.items.get().product,
            price=60.0,
            size=1,
            valid_from=round_.growing_period.start_date - datetime.timedelta(days=30),
        )
        return bid, round_product

    def test_createContracts_solidarityMode_createsSolidarityContributionDifference(
        self, mock_capacity
    ):
        mock_capacity.return_value = []
        round_ = create_closed_round()
        bid, _ = self._create_bid(round_)
        ContractCreator.create_contracts_from_bids(round_, actor=bid.member, cache={})

        contribution = SolidarityContribution.objects.get(member=bid.member)
        self.assertEqual(Decimal("20.00"), contribution.amount)

    def test_createContracts_replacesExistingFutureSubscription(self, mock_capacity):
        mock_capacity.return_value = []
        round_ = create_closed_round()
        bid, _ = self._create_bid(round_)
        item_product = bid.items.get().product
        existing = SubscriptionFactory.create(
            member=bid.member,
            product=item_product,
            period=round_.growing_period,
            cancellation_ts=None,
        )

        ContractCreator.create_contracts_from_bids(round_, actor=bid.member, cache={})

        self.assertFalse(Subscription.objects.filter(id=existing.id).exists())
        self.assertEqual(
            1,
            Subscription.objects.filter(
                member=bid.member, period=round_.growing_period
            ).count(),
        )

    def test_createContracts_unconfirmedBidInScope_raisesValidationError(
        self, mock_capacity
    ):
        mock_capacity.return_value = []
        round_ = create_closed_round()
        confirmed_bid, _ = self._create_bid(round_)
        not_confirmed_bid, _ = self._create_bid(round_, admin_confirmed=False)

        with self.assertRaises(ValidationError):
            ContractCreator.create_contracts_from_bids(
                round_, actor=confirmed_bid.member, cache={}
            )

        self.assertEqual(
            0, Subscription.objects.filter(member=confirmed_bid.member).count()
        )
        self.assertEqual(
            0, Subscription.objects.filter(member=not_confirmed_bid.member).count()
        )

    def test_createContracts_onlyConfirmedBidSelected_createsOnlyThatContract(
        self, mock_capacity
    ):
        mock_capacity.return_value = []
        round_ = create_closed_round()
        confirmed_bid, _ = self._create_bid(round_)
        not_confirmed_bid, _ = self._create_bid(round_, admin_confirmed=False)

        ContractCreator.create_contracts_from_bids(
            round_,
            bid_ids=[confirmed_bid.id],
            actor=confirmed_bid.member,
            cache={},
        )

        self.assertEqual(
            1, Subscription.objects.filter(member=confirmed_bid.member).count()
        )
        self.assertEqual(
            0, Subscription.objects.filter(member=not_confirmed_bid.member).count()
        )

    @patch.object(
        MemberPickupLocationSetter, "link_member_to_pickup_location", autospec=True
    )
    def test_createContracts_pickupLocationsEnabled_linksMemberToPickupLocation(
        self, mock_link, mock_capacity
    ):
        mock_capacity.return_value = []
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        round_ = create_closed_round()
        pickup_location = PickupLocationFactory.create()
        bid, _ = self._create_bid(round_, pickup_location=pickup_location)

        ContractCreator.create_contracts_from_bids(round_, actor=bid.member, cache={})

        mock_link.assert_called_once()
        call_kwargs = mock_link.call_args.kwargs
        self.assertEqual(pickup_location.id, call_kwargs["pickup_location_id"])
        self.assertEqual(bid.member, call_kwargs["member"])
        self.assertEqual(round_.growing_period.start_date, call_kwargs["valid_from"])
        self.assertEqual(bid.member, call_kwargs["actor"])

    @patch.object(
        MemberPickupLocationSetter, "link_member_to_pickup_location", autospec=True
    )
    def test_createContracts_pickupLocationsDisabled_skipsLinking(
        self, mock_link, mock_capacity
    ):
        mock_capacity.return_value = []
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="false")
        round_ = create_closed_round()
        pickup_location = PickupLocationFactory.create()
        bid, _ = self._create_bid(round_, pickup_location=pickup_location)

        ContractCreator.create_contracts_from_bids(round_, actor=bid.member, cache={})

        mock_link.assert_not_called()
        self.assertFalse(
            MemberPickupLocation.objects.filter(member=bid.member).exists()
        )

    def test_createContracts_capacityConflict_returnsErrorReportWithoutRollback(
        self, mock_capacity
    ):
        round_ = create_closed_round()
        bid, round_product = self._create_bid(round_)
        mock_capacity.return_value = [round_product.product_type_id]

        result = ContractCreator.create_contracts_from_bids(
            round_, actor=bid.member, cache={}
        )

        self.assertEqual(1, len(result["errors"]))
        self.assertEqual(0, Subscription.objects.filter(member=bid.member).count())
        round_.refresh_from_db()
        self.assertIsNotNone(round_.contracts_created_at)

    def test_createContracts_setsContractsCreatedAt(self, mock_capacity):
        mock_capacity.return_value = []
        round_ = create_closed_round()
        bid, _ = self._create_bid(round_)

        ContractCreator.create_contracts_from_bids(round_, actor=bid.member, cache={})

        round_.refresh_from_db()
        self.assertIsNotNone(round_.contracts_created_at)

    def test_createContracts_withBidIds_onlySelectedBidsProcessed(self, mock_capacity):
        mock_capacity.return_value = []
        round_ = create_closed_round()
        selected_bid, _ = self._create_bid(round_)
        other_bid, _ = self._create_bid(round_)

        ContractCreator.create_contracts_from_bids(
            round_, bid_ids=[selected_bid.id], actor=selected_bid.member, cache={}
        )

        self.assertEqual(
            1, Subscription.objects.filter(member=selected_bid.member).count()
        )
        self.assertEqual(
            0, Subscription.objects.filter(member=other_bid.member).count()
        )

    def test_createContracts_requiresClosedRound(self, mock_capacity):
        round_ = BiddingRoundFactory.create(status=ACTIVE)
        with self.assertRaises(ValidationError):
            ContractCreator.create_contracts_from_bids(round_, cache={})

    def test_createContracts_lockedAtRedPosition_usesRedAmount(self, mock_capacity):
        mock_capacity.return_value = []
        round_ = create_closed_round(position=Decimal("100"))
        round_.bid_levels = 3
        round_.save()
        bid, _ = self._create_bid(
            round_,
            amount_1=Decimal("60.00"),
            amount_2=Decimal("80.00"),
            amount_3=Decimal("100.00"),
        )
        ContractCreator.create_contracts_from_bids(round_, actor=bid.member, cache={})

        contribution = SolidarityContribution.objects.get(member=bid.member)
        self.assertEqual(Decimal("40.00"), contribution.amount)

    def test_createContracts_lockedSurchargeOnBids_appliesSurchargeToPrice(
        self, mock_capacity
    ):
        mock_capacity.return_value = []
        round_ = create_closed_round(position=Decimal("50"))
        round_.locked_surcharge_percent = Decimal("10")
        round_.locked_surcharge_on_bids = True
        round_.save()
        bid, _ = self._create_bid(
            round_,
            amount_1=Decimal("100.00"),
            amount_2=Decimal("100.00"),
            amount_3=Decimal("100.00"),
        )
        ContractCreator.create_contracts_from_bids(round_, actor=bid.member, cache={})

        contribution = SolidarityContribution.objects.get(member=bid.member)
        self.assertEqual(Decimal("50.00"), contribution.amount)

    def test_createContracts_linksCreatedSubscriptionsToRound(self, mock_capacity):
        mock_capacity.return_value = []
        round_ = create_closed_round()
        bid, _ = self._create_bid(round_)

        ContractCreator.create_contracts_from_bids(round_, actor=bid.member, cache={})

        self.assertEqual(1, round_.created_subscriptions.count())
        link = round_.created_subscriptions.get()
        self.assertTrue(link.is_bidder_contract)
        self.assertEqual(
            Subscription.objects.get(
                member=bid.member, period=round_.growing_period
            ).id,
            link.subscription_id,
        )

    def test_createContracts_withBidLevel_usesLevelAmount(self, mock_capacity):
        mock_capacity.return_value = []
        round_ = create_closed_round(position=Decimal("50"))
        round_.bid_levels = 3
        round_.save()
        bid, _ = self._create_bid(
            round_,
            amount_1=Decimal("60.00"),
            amount_2=Decimal("80.00"),
            amount_3=Decimal("100.00"),
        )

        ContractCreator.create_contracts_from_bids(
            round_, actor=bid.member, cache={}, bid_level=3
        )

        contribution = SolidarityContribution.objects.get(member=bid.member)
        self.assertEqual(Decimal("40.00"), contribution.amount)


class TestContractCreatorCapacityWithWaitingList(TapirIntegrationTest):
    """The real global capacity check must not be blocked by the waiting list
    reservation (which is a single-order safeguard, not meant for a whole round)."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_createContracts_largeWaitingListReservation_stillCreatesContracts(self):
        round_ = create_closed_round()
        round_product, product = create_round_product_with_product(round_, capacity=1)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("60.00"),
            size=1,
            valid_from=round_.growing_period.start_date - datetime.timedelta(days=30),
        )

        member = MemberFactory.create()
        bid = BidFactory.create(round=round_, member=member, admin_confirmed=get_now())
        BidItemFactory.create(
            bid=bid,
            round_product=round_product,
            product=product,
            quantity=1,
            amount_1=Decimal("80.00"),
        )

        waiting_list_entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=waiting_list_entry, product=product, quantity=10
        )

        result = ContractCreator.create_contracts_from_bids(
            round_, actor=member, cache={}
        )

        self.assertEqual([], result["errors"])
        self.assertTrue(
            Subscription.objects.filter(
                member=member, period=round_.growing_period
            ).exists()
        )


class TestContractCreatorAutoRenewed(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)

    def _prepare_round_with_renewal(self):
        round_ = create_closed_round()
        GrowingPeriodFactory.create(
            start_date=round_.growing_period.start_date - relativedelta(years=1),
            end_date=round_.growing_period.start_date - datetime.timedelta(days=1),
        )
        _, product = create_round_product_with_product(round_, capacity=10)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("77.00"),
            size=1,
            valid_from=round_.growing_period.start_date - relativedelta(years=1),
        )
        previous_period = GrowingPeriod.objects.get(
            end_date=round_.growing_period.start_date - datetime.timedelta(days=1)
        )
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=previous_period,
            product=product,
            quantity=1,
            start_date=previous_period.start_date,
            end_date=previous_period.end_date,
        )
        return round_, member

    def test_createContracts_withAutoRenewedFlag_createsRenewedSubscription(self):
        round_, member = self._prepare_round_with_renewal()

        ContractCreator.create_contracts_from_bids(
            round_, cache={}, create_auto_renewed_contracts=True
        )

        self.assertTrue(
            Subscription.objects.filter(
                member=member, period=round_.growing_period
            ).exists()
        )
        link = BiddingRoundCreatedSubscription.objects.get(
            round=round_, subscription__member=member
        )
        self.assertFalse(link.is_bidder_contract)

    def test_createContracts_withAutoRenewedFlagButMemberNotSelected_createsNothing(
        self,
    ):
        round_, member = self._prepare_round_with_renewal()

        ContractCreator.create_contracts_from_bids(
            round_,
            cache={},
            create_auto_renewed_contracts=True,
            auto_renewed_member_ids=["not-the-member"],
        )

        self.assertFalse(
            Subscription.objects.filter(
                member=member, period=round_.growing_period
            ).exists()
        )

    def test_createContracts_withoutAutoRenewedFlag_createsNothing(self):
        round_, member = self._prepare_round_with_renewal()

        ContractCreator.create_contracts_from_bids(round_, cache={})

        self.assertFalse(
            Subscription.objects.filter(
                member=member, period=round_.growing_period
            ).exists()
        )

    def test_autoRenewedEvaluation_stableBeforeAndAfterContractCreation(self):
        round_, member = self._prepare_round_with_renewal()

        before = BiddingRoundStatsService.get_auto_renewed_by_member(round_, cache={})
        self.assertIn(member.id, before)
        shares_before = before[member.id]["shares"]

        ContractCreator.create_contracts_from_bids(
            round_, cache={}, create_auto_renewed_contracts=True
        )

        after = BiddingRoundStatsService.get_auto_renewed_by_member(round_, cache={})
        self.assertIn(member.id, after)
        self.assertEqual(shares_before, after[member.id]["shares"])
        self.assertGreater(after[member.id]["shares"], 0)
