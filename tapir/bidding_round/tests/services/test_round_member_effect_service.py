from decimal import Decimal

from tapir.bidding_round.models import BiddingRoundMemberEffect
from tapir.bidding_round.services.round_member_effect_service import (
    RoundMemberEffectService,
)
from tapir.bidding_round.tests.factories import BiddingRoundFactory
from tapir.solidarity_contribution.models import (
    SolidarityContributionChangedLogEntry,
)
from tapir.solidarity_contribution.tests.factories import (
    SolidarityContributionFactory,
)
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestRoundMemberEffectService(TapirIntegrationTest):
    def setUp(self):
        super().setUp()
        self.period = GrowingPeriodFactory.create()
        self.bidding_round = BiddingRoundFactory.create(growing_period=self.period)
        self.member = MemberFactory.create()
        self.product = ProductFactory.create()

    def _subscription(self, quantity=1):
        return SubscriptionFactory.create(
            member=self.member,
            product=self.product,
            period=self.period,
            quantity=quantity,
        )

    def _change_quantity(self, subscription, quantity, source=None):
        with RoundMemberEffectService.track(
            self.bidding_round,
            self.member,
            source or BiddingRoundMemberEffect.Source.BID,
            actor=None,
            cache={},
        ) as tracked:
            subscription.quantity = quantity
            subscription.save(update_fields=["quantity", "updated_at"])
        return tracked

    def test_track_withSubscriptionChange_recordsAppliedEffect(self):
        subscription = self._subscription()

        tracked = self._change_quantity(subscription, 3)

        self.assertTrue(tracked.changed)
        effect = tracked.effect
        self.assertEqual(BiddingRoundMemberEffect.State.APPLIED, effect.state)
        self.assertEqual(BiddingRoundMemberEffect.Source.BID, effect.source)
        self.assertIsNotNone(effect.applied_at)
        self.assertEqual(1, effect.previous_subscriptions[0]["fields"]["quantity"])
        self.assertEqual(3, effect.applied_subscriptions[0]["fields"]["quantity"])
        self.assertTrue(BiddingRoundMemberEffect.objects.filter(pk=effect.pk).exists())

    def test_track_withoutChange_leavesNoEffectBehind(self):
        self._subscription()

        with RoundMemberEffectService.track(
            self.bidding_round,
            self.member,
            BiddingRoundMemberEffect.Source.NON_BIDDER_FLOOR,
            actor=None,
            cache={},
        ) as tracked:
            pass

        self.assertFalse(tracked.changed)
        self.assertFalse(
            BiddingRoundMemberEffect.objects.filter(
                round=self.bidding_round, member=self.member
            ).exists()
        )

    def test_track_withExistingAppliedEffect_keepsTheFirstPreviousState(self):
        subscription = self._subscription()
        self._change_quantity(subscription, 2)

        tracked = self._change_quantity(
            subscription,
            4,
            source=BiddingRoundMemberEffect.Source.NON_BIDDER_FLOOR,
        )

        effect = tracked.effect
        self.assertEqual(1, effect.previous_subscriptions[0]["fields"]["quantity"])
        self.assertEqual(4, effect.applied_subscriptions[0]["fields"]["quantity"])
        self.assertEqual(BiddingRoundMemberEffect.Source.BID, effect.source)
        self.assertEqual(1, BiddingRoundMemberEffect.objects.count())

    def test_track_withExistingReversedEffect_rebuildsTheEffect(self):
        subscription = self._subscription()
        tracked = self._change_quantity(subscription, 2)
        effect = tracked.effect
        effect.state = BiddingRoundMemberEffect.State.REVERSED
        effect.reversed_at = get_now(cache={})
        effect.reversal_reason = "alter Rollback"
        effect.save()

        tracked = self._change_quantity(subscription, 5)

        effect = tracked.effect
        self.assertEqual(BiddingRoundMemberEffect.State.APPLIED, effect.state)
        self.assertIsNone(effect.reversed_at)
        self.assertEqual("", effect.reversal_reason)
        self.assertEqual(2, effect.previous_subscriptions[0]["fields"]["quantity"])
        self.assertEqual(5, effect.applied_subscriptions[0]["fields"]["quantity"])

    def test_track_withContributionChange_recordsContributionSnapshots(self):
        contribution = SolidarityContributionFactory.create(
            member=self.member, amount=Decimal("10.00")
        )
        contribution_id = contribution.pk

        with RoundMemberEffectService.track(
            self.bidding_round,
            self.member,
            BiddingRoundMemberEffect.Source.NON_BIDDER_FLOOR,
            actor=None,
            cache={},
        ) as tracked:
            contribution.delete()

        effect = tracked.effect
        self.assertEqual(
            [contribution_id],
            [entry["pk"] for entry in effect.previous_contributions],
        )
        self.assertEqual([], effect.applied_contributions)

    def test_contributionLogLinks_findsEntriesReferencingTheContribution(self):
        contribution = SolidarityContributionFactory.create(member=self.member)
        log_entry = SolidarityContributionChangedLogEntry.objects.create(
            old_contribution_amount=Decimal("10.00"),
            old_contribution_end_date=contribution.end_date,
            new_contribution_amount=Decimal("10.00"),
            new_contribution_start_date=contribution.start_date,
            old_contribution=contribution,
            new_contribution=contribution,
        )

        links = RoundMemberEffectService.contribution_log_links(
            RoundMemberEffectService.contributions_state(self.member)
        )

        self.assertEqual([log_entry.pk], [link["pk"] for link in links])
        self.assertEqual(contribution.pk, links[0]["old_contribution_id"])
        self.assertEqual(contribution.pk, links[0]["new_contribution_id"])

    def test_currentState_matchesTheAppliedSnapshots(self):
        subscription = self._subscription()
        tracked = self._change_quantity(subscription, 2)
        effect = tracked.effect

        subscriptions, contributions = RoundMemberEffectService.current_state(effect)

        self.assertEqual(effect.applied_subscriptions, subscriptions)
        self.assertEqual(effect.applied_contributions, contributions)

    def test_appliedEffectAndHasAppliedEffects_respectTheState(self):
        subscription = self._subscription()
        effect = self._change_quantity(subscription, 2).effect

        self.assertEqual(
            effect,
            RoundMemberEffectService.applied_effect(self.bidding_round, self.member),
        )
        self.assertTrue(
            RoundMemberEffectService.has_applied_effects(self.bidding_round)
        )

        effect.state = BiddingRoundMemberEffect.State.REVERSED
        effect.save()

        self.assertIsNone(
            RoundMemberEffectService.applied_effect(self.bidding_round, self.member)
        )
        self.assertFalse(
            RoundMemberEffectService.has_applied_effects(self.bidding_round)
        )

    def test_mandateRefIds_tracksNewReferences(self):
        previous_ids = RoundMemberEffectService.mandate_ref_ids(self.member)

        with RoundMemberEffectService.track(
            self.bidding_round,
            self.member,
            BiddingRoundMemberEffect.Source.BID,
            actor=None,
            cache={},
        ) as tracked:
            subscription = SubscriptionFactory.create(
                member=self.member, product=self.product, period=self.period
            )
            subscription.quantity = 2
            subscription.save(update_fields=["quantity", "updated_at"])

        effect = tracked.effect
        self.assertEqual(previous_ids, effect.previous_mandate_ref_ids)
        self.assertEqual(1, len(effect.created_mandate_ref_ids))
        self.assertIn(
            effect.created_mandate_ref_ids[0],
            RoundMemberEffectService.mandate_ref_ids(self.member),
        )

    def test_track_withChangeOnAnotherPeriod_doesNotRecordTheSubscription(self):
        other_period = GrowingPeriodFactory.create()
        other_subscription = SubscriptionFactory.create(
            member=self.member, product=self.product, period=other_period
        )

        with RoundMemberEffectService.track(
            self.bidding_round,
            self.member,
            BiddingRoundMemberEffect.Source.BID,
            actor=None,
            cache={},
        ) as tracked:
            other_subscription.quantity = 2
            other_subscription.save(update_fields=["quantity", "updated_at"])

        self.assertFalse(tracked.changed)
