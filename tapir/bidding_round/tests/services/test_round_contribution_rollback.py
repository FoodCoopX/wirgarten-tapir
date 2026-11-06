import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError

from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.services.contract_deletion_service import (
    BiddingRoundContractDeletionService,
)
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.solidarity_contribution.models import (
    SolidarityContribution,
    SolidarityContributionChangedLogEntry,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now
from tapir.utils.services.tapir_cache import TapirCache


class TestRoundContributionRollback(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="false")
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value="true")
        self.round = create_open_round()
        self.round_product, self.product = create_round_product_with_product(
            self.round, target_amount_per_year=Decimal("1000"), capacity=100
        )
        ProductPriceFactory.create(
            product=self.product,
            price=Decimal("60"),
            size=1,
            valid_from=self.round.growing_period.start_date,
        )
        self.member = MemberFactory.create()

    def _renewing_nonbidder(self):
        member = MemberFactory.create()
        previous = GrowingPeriodFactory.create(
            start_date=self.round.growing_period.start_date
            - datetime.timedelta(days=365),
            end_date=self.round.growing_period.start_date - datetime.timedelta(days=1),
        )
        SubscriptionFactory.create(
            member=member, product=self.product, period=previous, quantity=1
        )
        renewals = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                self.round.growing_period.start_date, cache={}
            )
        )
        self.assertIn(member.pk, {s.member_id for s in renewals})
        return member

    def _contribution(self, member, amount):
        return SolidarityContribution.objects.create(
            member=member,
            amount=amount,
            start_date=self.round.growing_period.start_date,
            end_date=self.round.growing_period.end_date,
        )

    def _generate(self):
        bid = BiddingRoundService.save_bid(
            self.member,
            self.round,
            [build_item(self.round_product, self.product, amount_1="80")],
            cache={},
        )
        bid.admin_confirmed = get_now()
        bid.save()
        BiddingRoundService.close_round(self.round, cache={})
        BiddingRoundService.lock_average_bid(self.round, 0, 0, False, False, cache={})
        self.round.refresh_from_db()
        result = ContractCreator.create_contracts_from_bids(
            self.round, actor=self.member, cache={}
        )
        self.round.refresh_from_db()
        return result

    def _delete(self, cache=None):
        BiddingRoundContractDeletionService.delete_contracts(
            self.round, actor=self.member, cache={} if cache is None else cache
        )

    def test_bidder_prior_agreement_and_log_links_are_restored(self):
        prior = self._contribution(self.member, Decimal("7"))
        log = SolidarityContributionChangedLogEntry()
        log.populate_solidarity_contribution(self.member, self.member, None, prior)
        log.save()
        self._generate()
        self.assertEqual(
            Decimal("20"),
            SolidarityContribution.objects.get(member=self.member).amount,
        )
        self._delete()
        restored = SolidarityContribution.objects.get(member=self.member)
        self.assertEqual(prior.pk, restored.pk)
        self.assertEqual(Decimal("7"), restored.amount)
        self.assertEqual(prior.end_date, restored.end_date)
        self.assertIsNone(restored.cancellation_ts)
        log.refresh_from_db()
        self.assertEqual(restored.pk, log.new_contribution_id)

    def test_no_prior_agreement_removes_only_round_contribution(self):
        unrelated_member = MemberFactory.create()
        unrelated = self._contribution(unrelated_member, Decimal("11"))
        past = self._contribution(self.member, Decimal("5"))
        past.end_date = self.round.growing_period.start_date - datetime.timedelta(
            days=2
        )
        past.start_date = past.end_date - datetime.timedelta(days=30)
        past.save()
        self._generate()
        self._delete()
        self.assertEqual(
            [past.pk],
            list(
                SolidarityContribution.objects.filter(member=self.member).values_list(
                    "pk", flat=True
                )
            ),
        )
        unrelated.refresh_from_db()
        self.assertEqual(Decimal("11"), unrelated.amount)
        self.assertFalse(Subscription.objects.filter(member=self.member).exists())
        with self.assertRaises(ValidationError):
            self._delete()

    def test_untouched_nonbidder_agreement_survives_deletion(self):
        nonbidder = self._renewing_nonbidder()
        prior = self._contribution(nonbidder, Decimal("100"))
        self._generate()
        self._delete()
        prior.refresh_from_db()
        self.assertEqual(Decimal("100"), prior.amount)
        self.assertIsNone(prior.cancellation_ts)

    def test_changed_nonbidder_floor_restores_previous_agreement(self):
        nonbidder = self._renewing_nonbidder()
        prior = self._contribution(nonbidder, Decimal("7"))
        self._generate()
        self.assertEqual(
            Decimal("20"), SolidarityContribution.objects.get(member=nonbidder).amount
        )
        self._delete()
        restored = SolidarityContribution.objects.get(member=nonbidder)
        self.assertEqual(prior.pk, restored.pk)
        self.assertEqual(Decimal("7"), restored.amount)

    def test_later_independent_edit_blocks_destructive_rollback(self):
        self._generate()
        MemberSolidarityContributionService.assign_contribution_to_member(
            self.member,
            self.round.growing_period.start_date,
            Decimal("9"),
            cache={},
            actor=self.member,
        )
        with self.assertRaises(ValidationError):
            self._delete()
        self.assertTrue(Subscription.objects.filter(member=self.member).exists())
        self.assertEqual(
            Decimal("9"), SolidarityContribution.objects.get(member=self.member).amount
        )

    def test_delete_and_regenerate_preserve_baseline_and_same_request_cache(self):
        prior = self._contribution(self.member, Decimal("7"))
        self._generate()
        cache = {}
        self.assertEqual(
            Decimal("20"),
            TapirCache.get_member_solidarity_contribution_at_date(
                self.member.pk, self.round.growing_period.start_date, cache
            ),
        )
        self._delete(cache)
        self.assertEqual(
            Decimal("7"),
            TapirCache.get_member_solidarity_contribution_at_date(
                self.member.pk, self.round.growing_period.start_date, cache
            ),
        )
        ContractCreator.create_contracts_from_bids(
            self.round, actor=self.member, cache=cache
        )
        self.assertEqual(
            Decimal("20"), SolidarityContribution.objects.get(member=self.member).amount
        )
        self._delete(cache)
        self.assertEqual(
            prior.pk, SolidarityContribution.objects.get(member=self.member).pk
        )
        self.assertEqual(
            Decimal("7"),
            TapirCache.get_member_solidarity_contribution_at_date(
                self.member.pk, self.round.growing_period.start_date, cache
            ),
        )

    def test_legacy_round_without_baseline_cannot_delete_financial_state(self):
        subscription = SubscriptionFactory.create(
            member=self.member,
            product=self.product,
            period=self.round.growing_period,
            quantity=1,
        )
        self.round.created_subscriptions.create(subscription=subscription)
        self.round.contracts_created_at = get_now()
        self.round.save()
        prior = self._contribution(self.member, Decimal("9"))
        with self.assertRaisesMessage(
            ValidationError, "frühere Solidaritätsbeitragsstand"
        ):
            self._delete()
        self.assertTrue(Subscription.objects.filter(pk=subscription.pk).exists())
        prior.refresh_from_db()
        self.assertEqual(Decimal("9"), prior.amount)
        self.round.refresh_from_db()
        self.assertIsNotNone(self.round.contracts_created_at)

    def test_all_rejected_bids_leave_no_unrecoverable_nonbidder_floor(self):
        nonbidder = self._renewing_nonbidder()
        prior = self._contribution(nonbidder, Decimal("7"))
        with patch.object(
            ContractCreator,
            "_check_capacity",
            side_effect=ValidationError("capacity exhausted"),
        ):
            result = self._generate()
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["subscriptions"])
        self.assertEqual([], result["non_bidder_member_ids"])
        prior.refresh_from_db()
        self.assertEqual(Decimal("7"), prior.amount)
        self.assertIsNone(prior.cancellation_ts)
        self.assertFalse(self.round.contribution_changes_tracked)
        self.assertIsNone(self.round.contracts_created_at)
        self.assertFalse(self.round.biddingroundcontributionchange_set.exists())

    def test_partial_success_remains_reversible_with_error_report(self):
        nonbidder = self._renewing_nonbidder()
        prior = self._contribution(nonbidder, Decimal("7"))
        failed_member = MemberFactory.create()
        bid = BiddingRoundService.save_bid(
            failed_member,
            self.round,
            [build_item(self.round_product, self.product, amount_1="90")],
            cache={},
        )
        bid.admin_confirmed = get_now()
        bid.save()
        original = ContractCreator._check_capacity

        def reject_one(bid, cache):
            if bid.member_id == failed_member.pk:
                raise ValidationError("capacity exhausted")
            return original(bid, cache=cache)

        with patch.object(ContractCreator, "_check_capacity", side_effect=reject_one):
            result = self._generate()
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual(1, len(result["subscriptions"]))
        self.assertTrue(self.round.contribution_changes_tracked)
        self.assertIsNotNone(self.round.contracts_created_at)
        self.assertFalse(Subscription.objects.filter(member=failed_member).exists())
        self._delete()
        restored = SolidarityContribution.objects.get(member=nonbidder)
        self.assertEqual(prior.pk, restored.pk)
        self.assertEqual(Decimal("7"), restored.amount)
