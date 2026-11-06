import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse

from tapir.bidding_round.config import ACTIVE
from tapir.bidding_round.models import BiddingRoundReplacedSubscription
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.services.contract_deletion_service import (
    BiddingRoundContractDeletionService,
)
from tapir.bidding_round.tests.factories import (
    BiddingRoundFactory,
    BiddingRoundProductFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.configuration.models import TapirParameter
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.wirgarten.utils import get_now


class TestCrossRoundContractReplacement(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, get_now().replace(microsecond=0))
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(
            ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED, False
        )
        self.first = create_open_round()
        self.first_product, self.product = create_round_product_with_product(
            self.first, target_amount_per_year=Decimal("1000"), capacity=100
        )
        ProductPriceFactory.create(
            product=self.product,
            price=Decimal("60"),
            size=1,
            valid_from=self.first.growing_period.start_date,
        )
        self.member = MemberFactory.create()
        self.admin = MemberFactory.create(is_superuser=True)
        self.apiClient.force_authenticate(self.admin)

    def _bid(self, round_, round_product, member, amount):
        bid = BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, self.product, amount_1=amount)],
            cache={},
        )
        bid.admin_confirmed = get_now()
        bid.save()
        return bid

    def _close(self, round_):
        BiddingRoundService.close_round(round_, cache={})
        BiddingRoundService.lock_average_bid(round_, 0, 0, False, False, cache={})
        round_.refresh_from_db()

    def _second_round(self):
        now = get_now()
        round_ = BiddingRoundFactory.create(
            growing_period=self.first.growing_period,
            status=ACTIVE,
            start_at=now - datetime.timedelta(days=1),
            end_at=now + datetime.timedelta(days=1),
        )
        product = BiddingRoundProductFactory.create(
            round=round_,
            product_type=self.product.type,
            target_amount_per_year=Decimal("1000"),
        )
        BiddingRoundProductPriceFactory.create(
            round_product=product,
            product=self.product,
            reference_value=80,
            min_amount=60,
        )
        return round_, product

    def _create_api(self, round_):
        response = self.apiClient.post(
            reverse("bidding_rounds:create_contracts", args=[round_.pk]),
            {},
            format="json",
        )
        self.assertStatusCode(response, 200)
        return response

    def test_second_round_api_and_delete_restore_exact_first_round_state(self):
        self._bid(self.first, self.first_product, self.member, "80")
        self._close(self.first)
        self._create_api(self.first)
        subscription_before = list(
            Subscription.objects.filter(member=self.member).values()
        )
        links_before = list(self.first.created_subscriptions.values())
        solidarity_before = list(
            SolidarityContribution.objects.filter(member=self.member).values()
        )
        self.first.refresh_from_db()
        first_timestamp = self.first.contracts_created_at
        second, product = self._second_round()
        self._bid(second, product, self.member, "90")
        self._close(second)
        self._create_api(second)
        self.assertEqual(1, Subscription.objects.filter(member=self.member).count())
        self.assertEqual(
            Decimal("30"), SolidarityContribution.objects.get(member=self.member).amount
        )
        BiddingRoundContractDeletionService.delete_contracts(
            second, self.admin, cache={}
        )
        self.assertEqual(
            subscription_before,
            list(Subscription.objects.filter(member=self.member).values()),
        )
        self.assertEqual(links_before, list(self.first.created_subscriptions.values()))
        self.assertEqual(
            solidarity_before,
            list(SolidarityContribution.objects.filter(member=self.member).values()),
        )
        self.first.refresh_from_db()
        self.assertEqual(first_timestamp, self.first.contracts_created_at)
        with self.assertRaises(ValidationError):
            BiddingRoundContractDeletionService.delete_contracts(
                second, self.admin, cache={}
            )
        self.assertEqual(1, Subscription.objects.filter(member=self.member).count())

    def test_unexpected_second_bid_failure_rolls_back_entire_generation(self):
        first_member = self.member
        second_member = MemberFactory.create()
        self._bid(self.first, self.first_product, first_member, "80")
        self._bid(self.first, self.first_product, second_member, "90")
        self._close(self.first)
        original = ContractCreator._create_contracts_for_bid
        completed = []

        def fail_second(*args, **kwargs):
            if completed:
                raise RuntimeError("second bid failed")
            result = original(*args, **kwargs)
            completed.append(result)
            return result

        with patch.object(
            ContractCreator, "_create_contracts_for_bid", side_effect=fail_second
        ):
            with self.assertRaisesMessage(RuntimeError, "second bid failed"):
                ContractCreator.create_contracts_from_bids(
                    self.first, actor=self.admin, cache={}
                )
        self.assertEqual(1, len(completed))
        self.assertFalse(
            Subscription.objects.filter(
                member__in=[first_member, second_member]
            ).exists()
        )
        self.assertFalse(
            SolidarityContribution.objects.filter(
                member__in=[first_member, second_member]
            ).exists()
        )
        self.first.refresh_from_db()
        self.assertIsNone(self.first.contracts_created_at)
        self.assertFalse(self.first.contribution_changes_tracked)

    def test_restore_failure_keeps_new_contract_contribution_and_snapshot(self):
        self._bid(self.first, self.first_product, self.member, "80")
        self._close(self.first)
        self._create_api(self.first)
        second, product = self._second_round()
        self._bid(second, product, self.member, "90")
        self._close(second)
        self._create_api(second)
        current_subscription = Subscription.objects.get(member=self.member)
        current_contribution = SolidarityContribution.objects.get(member=self.member)
        with patch.object(
            BiddingRoundReplacedSubscription,
            "restore",
            side_effect=RuntimeError("restore failed"),
        ):
            with self.assertRaisesMessage(RuntimeError, "restore failed"):
                BiddingRoundContractDeletionService.delete_contracts(
                    second, self.admin, cache={}
                )
        self.assertTrue(
            Subscription.objects.filter(pk=current_subscription.pk).exists()
        )
        self.assertTrue(
            SolidarityContribution.objects.filter(
                pk=current_contribution.pk, amount=Decimal("30")
            ).exists()
        )
        self.assertTrue(second.replaced_subscriptions.exists())
        second.refresh_from_db()
        self.assertIsNotNone(second.contracts_created_at)
