from django.core.exceptions import ValidationError

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.contract_deletion_service import (
    BiddingRoundContractDeletionService,
)
from tapir.bidding_round.tests.helpers import (
    create_open_round,
    create_round_product_with_product,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBiddingRoundContractDeletionService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_deleteContracts_deletesLinkedSubscriptionsAndClearsTimestamp(self):
        round_ = create_open_round()
        _, product = create_round_product_with_product(round_, capacity=100)
        member = MemberFactory.create()
        subscription = SubscriptionFactory.create(
            member=member,
            period=round_.growing_period,
            product=product,
            quantity=1,
        )
        BiddingRoundCreatedSubscription.objects.create(
            round=round_, subscription=subscription, is_bidder_contract=True
        )
        round_.contracts_created_at = get_now()
        round_.save()

        BiddingRoundContractDeletionService.delete_contracts(
            round_, actor=member, cache={}
        )

        round_.refresh_from_db()
        self.assertIsNone(round_.contracts_created_at)
        self.assertFalse(Subscription.objects.filter(id=subscription.id).exists())
        self.assertEqual(0, round_.created_subscriptions.count())

    def test_deleteContracts_noContractsCreated_raisesValidationError(self):
        round_ = create_open_round()

        with self.assertRaises(ValidationError):
            BiddingRoundContractDeletionService.delete_contracts(
                round_, actor=None, cache={}
            )
