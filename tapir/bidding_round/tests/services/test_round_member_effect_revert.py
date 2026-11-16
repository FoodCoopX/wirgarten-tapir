import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CLOSED
from tapir.bidding_round.models import (
    BiddingRoundCreatedSubscription,
    BiddingRoundMemberEffect,
    BiddingRoundMemberRollbackLogEntry,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.services.round_member_effect_service import (
    MemberRollbackConflict,
    NoEffectsError,
    RoundMemberEffectService,
    UntrackedRoundError,
)
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
    BiddingRoundProductTypeFactory,
)
from tapir.solidarity_contribution.models import (
    SolidarityContribution,
    SolidarityContributionChangedLogEntry,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MandateReferenceFactory,
    MemberFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestRoundMemberEffectRevert(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _closed_round_with_bid(self, quantity=1):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period, status=BIDDING_ROUND_STATUS_CLOSED
        )
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type, product=product
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            quantity=quantity,
            amount_1=Decimal("80.00"),
        )
        BiddingRoundService.lock_average_bid(
            bidding_round,
            position=0,
            surcharge_percent=0,
            surcharge_on_bids=False,
            surcharge_on_average=False,
            cache={},
        )
        bid.admin_confirmed = get_now(cache={})
        bid.save()
        return bidding_round, bid, product, period

    @staticmethod
    def _renewing_subscription(member, product, period):
        previous_period = GrowingPeriodFactory.create(
            start_date=period.start_date - datetime.timedelta(days=365),
            end_date=period.start_date - datetime.timedelta(days=1),
        )
        current = SubscriptionFactory.create(
            member=member,
            product=product,
            period=previous_period,
            quantity=1,
            start_date=previous_period.start_date,
            end_date=previous_period.end_date,
        )
        renewed = SubscriptionFactory.build(
            member=member,
            product=product,
            period=period,
            quantity=1,
            start_date=period.start_date,
            end_date=period.end_date,
            mandate_ref=MandateReferenceFactory.create(member=member),
        )
        return current, renewed

    def _effect(self, bidding_round, member):
        return BiddingRoundMemberEffect.objects.get(round=bidding_round, member=member)

    def test_revertMember_restoresThePreState(self):
        bidding_round, bid, product, _period = self._closed_round_with_bid()
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )
        subscription = Subscription.objects.get(member=bid.member, product=product)

        result = RoundMemberEffectService.revert_member(
            bidding_round, bid.member, actor=bid.member, cache={}
        )

        self.assertEqual("reverted", result["state"])
        self.assertFalse(Subscription.objects.filter(pk=subscription.pk).exists())
        self.assertFalse(
            SolidarityContribution.objects.filter(member=bid.member).exists()
        )
        effect = self._effect(bidding_round, bid.member)
        self.assertEqual(BiddingRoundMemberEffect.State.REVERSED, effect.state)
        self.assertFalse(
            BiddingRoundCreatedSubscription.objects.filter(round=bidding_round).exists()
        )
        bidding_round.refresh_from_db()
        self.assertIsNone(bidding_round.contracts_created_at)
        log_entry = BiddingRoundMemberRollbackLogEntry.objects.get()
        self.assertEqual(bidding_round.name, log_entry.round_name)
        self.assertEqual(1, log_entry.subscriptions_deleted)

    def test_revertMember_withReusedSubscription_restoresAllFields(self):
        bidding_round, bid, product, period = self._closed_round_with_bid(quantity=3)
        existing = SubscriptionFactory.create(
            member=bid.member,
            product=product,
            period=period,
            quantity=1,
        )
        before = (
            existing.start_date,
            existing.end_date,
            existing.mandate_ref_id,
            existing.notice_period_duration,
            existing.notice_period_unit,
        )
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        RoundMemberEffectService.revert_member(
            bidding_round, bid.member, actor=bid.member, cache={}
        )

        existing.refresh_from_db()
        self.assertEqual(1, existing.quantity)
        self.assertEqual(
            before,
            (
                existing.start_date,
                existing.end_date,
                existing.mandate_ref_id,
                existing.notice_period_duration,
                existing.notice_period_unit,
            ),
        )

    def test_revertMember_keepsOtherMembersUntouched(self):
        bidding_round, bid, product, period = self._closed_round_with_bid()
        other_bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=other_bid,
            round_product_type=bidding_round.product_types.first(),
            product=product,
            amount_1=Decimal("90.00"),
        )
        other_bid.admin_confirmed = get_now(cache={})
        other_bid.save()
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )
        other_subscription = Subscription.objects.get(
            member=other_bid.member, product=product
        )

        RoundMemberEffectService.revert_member(
            bidding_round, bid.member, actor=bid.member, cache={}
        )

        self.assertTrue(Subscription.objects.filter(pk=other_subscription.pk).exists())
        self.assertEqual(
            BiddingRoundMemberEffect.State.APPLIED,
            self._effect(bidding_round, other_bid.member).state,
        )
        bidding_round.refresh_from_db()
        self.assertIsNotNone(bidding_round.contracts_created_at)

        RoundMemberEffectService.revert_member(
            bidding_round, other_bid.member, actor=bid.member, cache={}
        )
        bidding_round.refresh_from_db()
        self.assertIsNone(bidding_round.contracts_created_at)

    def test_revertMember_calledTwice_isSkipped(self):
        bidding_round, bid, _product, _period = self._closed_round_with_bid()
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )
        RoundMemberEffectService.revert_member(
            bidding_round, bid.member, actor=bid.member, cache={}
        )

        result = RoundMemberEffectService.revert_member(
            bidding_round, bid.member, actor=bid.member, cache={}
        )

        self.assertEqual("skipped", result["state"])
        self.assertEqual(1, BiddingRoundMemberRollbackLogEntry.objects.count())

    def test_revertMember_withDivergence_raisesWithoutWriting(self):
        bidding_round, bid, product, _period = self._closed_round_with_bid()
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )
        subscription = Subscription.objects.get(member=bid.member, product=product)
        subscription.quantity = 5
        subscription.save(update_fields=["quantity", "updated_at"])

        with pytest.raises(MemberRollbackConflict) as context:
            RoundMemberEffectService.revert_member(
                bidding_round, bid.member, actor=bid.member, cache={}
            )

        self.assertEqual("diverged", context.value.conflicts[0]["kind"])
        self.assertTrue(Subscription.objects.filter(pk=subscription.pk).exists())
        self.assertEqual(
            BiddingRoundMemberEffect.State.APPLIED,
            self._effect(bidding_round, bid.member).state,
        )
        self.assertEqual(0, BiddingRoundMemberRollbackLogEntry.objects.count())

    def test_revertMember_withDivergenceAndForce_restoresThePreState(self):
        bidding_round, bid, product, _period = self._closed_round_with_bid()
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )
        subscription = Subscription.objects.get(member=bid.member, product=product)
        subscription.quantity = 5
        subscription.save(update_fields=["quantity", "updated_at"])

        RoundMemberEffectService.revert_member(
            bidding_round,
            bid.member,
            actor=bid.member,
            reason="Korrektur",
            force=True,
            cache={},
        )

        self.assertFalse(Subscription.objects.filter(pk=subscription.pk).exists())
        effect = self._effect(bidding_round, bid.member)
        self.assertEqual(BiddingRoundMemberEffect.State.REVERSED, effect.state)
        self.assertTrue(effect.divergence_overridden)
        self.assertTrue(BiddingRoundMemberRollbackLogEntry.objects.get().forced)

    def test_revertMember_withForceWithoutReason_raisesValidationError(self):
        bidding_round, bid, _product, _period = self._closed_round_with_bid()
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        with pytest.raises(ValidationError):
            RoundMemberEffectService.revert_member(
                bidding_round, bid.member, actor=bid.member, force=True, cache={}
            )

    def test_revertMember_keepsPreExistingContributionOfNonBidder(self):
        bidding_round, bid, product, period = self._closed_round_with_bid()
        non_bidder = MemberFactory.create()
        current, _renewed = self._renewing_subscription(non_bidder, product, period)
        existing = SolidarityContribution.objects.create(
            member=non_bidder,
            amount=Decimal("200.00"),
            start_date=period.start_date,
            end_date=period.end_date,
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={current},
        ):
            ContractCreator.create_contracts_from_bids(
                bidding_round, cache={}, actor=bid.member
            )

        self.assertFalse(
            BiddingRoundMemberEffect.objects.filter(
                round=bidding_round, member=non_bidder
            ).exists()
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={current},
        ):
            RoundMemberEffectService.revert_member(
                bidding_round, bid.member, actor=bid.member, cache={}
            )

        existing.refresh_from_db()
        self.assertEqual(Decimal("200.00"), existing.amount)
        self.assertEqual(period.end_date, existing.end_date)

    def test_revertMember_restoresThePreviousContributionOfNonBidder(self):
        bidding_round, bid, product, period = self._closed_round_with_bid()
        non_bidder = MemberFactory.create()
        current, _renewed = self._renewing_subscription(non_bidder, product, period)
        previous = SolidarityContribution.objects.create(
            member=non_bidder,
            amount=Decimal("10.00"),
            start_date=period.start_date - datetime.timedelta(days=100),
            end_date=period.end_date,
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={current},
        ):
            ContractCreator.create_contracts_from_bids(
                bidding_round, cache={}, actor=bid.member
            )
            previous.refresh_from_db()
            self.assertIsNotNone(previous.cancellation_ts)
            RoundMemberEffectService.revert_member(
                bidding_round, non_bidder, actor=bid.member, cache={}
            )

        previous.refresh_from_db()
        self.assertIsNone(previous.cancellation_ts)
        self.assertEqual(period.end_date, previous.end_date)
        self.assertEqual(Decimal("10.00"), previous.amount)

    def test_revertMember_restoresContributionLogLinks(self):
        bidding_round, bid, product, period = self._closed_round_with_bid()
        non_bidder = MemberFactory.create()
        current, _renewed = self._renewing_subscription(non_bidder, product, period)
        previous = SolidarityContribution.objects.create(
            member=non_bidder,
            amount=Decimal("10.00"),
            start_date=period.start_date,
            end_date=period.end_date,
        )
        log_entry = SolidarityContributionChangedLogEntry.objects.create(
            old_contribution_amount=Decimal("10.00"),
            old_contribution_end_date=period.end_date,
            new_contribution_amount=Decimal("10.00"),
            new_contribution_start_date=period.start_date,
            old_contribution=previous,
            new_contribution=previous,
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={current},
        ):
            ContractCreator.create_contracts_from_bids(
                bidding_round, cache={}, actor=bid.member
            )
            RoundMemberEffectService.revert_member(
                bidding_round, non_bidder, actor=bid.member, cache={}
            )

        log_entry.refresh_from_db()
        self.assertEqual(previous.pk, log_entry.old_contribution_id)
        self.assertEqual(previous.pk, log_entry.new_contribution_id)

    def test_crossRoundConflicts_withSecondRoundEffect_reportsConflict(self):
        round_a, bid_a, product, _period = self._closed_round_with_bid()
        ContractCreator.create_contracts_from_bids(
            round_a, cache={}, actor=bid_a.member
        )
        subscription = Subscription.objects.get(member=bid_a.member, product=product)
        effect_a = BiddingRoundMemberEffect.objects.get(
            round=round_a, member=bid_a.member
        )

        round_b = BiddingRoundFactory.create(
            growing_period=round_a.growing_period,
            status=BIDDING_ROUND_STATUS_CLOSED,
        )
        BiddingRoundMemberEffect.objects.create(
            round=round_b,
            member=bid_a.member,
            source=BiddingRoundMemberEffect.Source.BID,
            previous_subscriptions=[{"pk": subscription.pk}],
            applied_subscriptions=[{"pk": subscription.pk}],
        )
        BiddingRoundCreatedSubscription.objects.create(
            round=round_b, subscription=subscription
        )

        conflicts = RoundMemberEffectService._cross_round_conflicts(effect_a)

        self.assertEqual(1, len(conflicts))
        self.assertEqual("cross_round", conflicts[0]["kind"])
        self.assertEqual(round_b.id, conflicts[0]["round_id"])

    def test_revertMembers_withUntrackedRound_raises(self):
        bidding_round = BiddingRoundFactory.create(
            contracts_created_at=get_now(cache={})
        )

        with pytest.raises(UntrackedRoundError):
            RoundMemberEffectService.revert_members(
                bidding_round, member_ids=None, actor=None, cache={}
            )

    def test_revertMembers_withoutContracts_raises(self):
        bidding_round = BiddingRoundFactory.create()

        with pytest.raises(NoEffectsError):
            RoundMemberEffectService.revert_members(
                bidding_round, member_ids=None, actor=None, cache={}
            )

    def test_revertMember_deletesMandateReferenceCreatedByTheRound(self):
        bidding_round, bid, _product, _period = self._closed_round_with_bid()
        self.assertEqual([], RoundMemberEffectService.mandate_ref_ids(bid.member))
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )
        self.assertEqual(1, len(RoundMemberEffectService.mandate_ref_ids(bid.member)))

        RoundMemberEffectService.revert_member(
            bidding_round, bid.member, actor=bid.member, cache={}
        )

        self.assertEqual([], RoundMemberEffectService.mandate_ref_ids(bid.member))
