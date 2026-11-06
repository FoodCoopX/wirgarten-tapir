from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.bidding_round.models import Bid
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
    ProductPriceFactory,
    PickupLocationFactory,
    PickupLocationCapabilityFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBidConfirmationChanges(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, True)
        self._set_parameter(
            ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED, False
        )
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
        self.admin = MemberFactory.create(is_superuser=True)
        self.item = build_item(self.round_product, self.product, amount_1="80")
        self.bid = BiddingRoundService.save_bid(
            self.member, self.round, [self.item], cache={}
        )
        self.bid.admin_confirmed = get_now()
        self.bid.save()

    def _member_post(self, item, **kwargs):
        self.apiClient.force_authenticate(self.member)
        response = self.apiClient.post(
            reverse("bidding_rounds:member_bid", args=[self.round.pk]),
            {"items": [item], **kwargs},
            format="json",
        )
        self.assertStatusCode(response, 200)
        self.bid.refresh_from_db()

    def test_changed_member_amount_requires_new_confirmation_before_contracts(self):
        self._member_post({**self.item, "amount_1": "120"})
        self.assertIsNone(self.bid.admin_confirmed)
        BiddingRoundService.close_round(self.round, cache={})
        BiddingRoundService.lock_average_bid(self.round, 0, 0, False, False, cache={})
        with self.assertRaises(ValidationError):
            ContractCreator.create_contracts_from_bids(
                self.round, actor=self.admin, cache={}
            )
        self.assertFalse(Subscription.objects.filter(member=self.member).exists())
        self.apiClient.force_authenticate(self.admin)
        response = self.apiClient.post(
            reverse("bidding_rounds:confirm_bids", args=[self.round.pk]),
            {"bid_ids": [str(self.bid.pk)]},
            format="json",
        )
        self.assertStatusCode(response, 200)
        result = ContractCreator.create_contracts_from_bids(
            self.round, actor=self.admin, cache={}
        )
        self.assertEqual(1, len(result["subscriptions"]))

    @patch.object(TransactionalTrigger, "fire_action")
    def test_identical_member_retry_preserves_confirmation_and_rows_without_mail(
        self, mock_fire
    ):
        confirmation = self.bid.admin_confirmed
        updated_at = self.bid.updated_at
        item_id = self.bid.items.get().pk
        self._member_post({**self.item, "amount_1": "80,00"})
        self._member_post({**self.item, "amount_1": "80.0"})
        self.assertEqual(confirmation, self.bid.admin_confirmed)
        self.assertEqual(updated_at, self.bid.updated_at)
        self.assertEqual(item_id, self.bid.items.get().pk)
        self.assertEqual(
            1, Bid.objects.filter(round=self.round, member=self.member).count()
        )
        mock_fire.assert_not_called()

    def test_member_quantity_change_invalidates_confirmation(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_BID_QUANTITY_ENABLED, True)
        self._member_post({**self.item, "quantity": 2})
        self.assertIsNone(self.bid.admin_confirmed)
        self.assertEqual(2, self.bid.items.get().quantity)

    def test_member_variant_change_invalidates_confirmation(self):
        variant = ProductFactory.create(type=self.product.type)
        ProductPriceFactory.create(
            product=variant,
            price=120,
            size=2,
            valid_from=self.round.growing_period.start_date,
        )
        self._member_post({**self.item, "product_id": variant.pk, "amount_1": "160"})
        self.assertIsNone(self.bid.admin_confirmed)

    def test_member_pickup_change_invalidates_confirmation(self):
        self._set_parameter(
            ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED, True
        )
        location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=location, product_type=self.product.type, max_capacity=100
        )
        self._member_post(self.item, pickup_location_id=location.pk)
        self.assertIsNone(self.bid.admin_confirmed)
        self.assertEqual(location.pk, self.bid.pickup_location_id)

    def test_admin_edit_clears_old_confirmation_unless_explicitly_confirmed(self):
        self.apiClient.force_authenticate(self.admin)
        url = reverse("bidding_rounds:bid_edit", args=[self.round.pk, self.bid.pk])
        response = self.apiClient.patch(
            url, {"items": [{**self.item, "amount_1": "120"}]}, format="json"
        )
        self.assertStatusCode(response, 200)
        self.bid.refresh_from_db()
        self.assertIsNone(self.bid.admin_confirmed)
        response = self.apiClient.patch(
            url,
            {"items": [{**self.item, "amount_1": "130"}], "admin_confirmed": True},
            format="json",
        )
        self.assertStatusCode(response, 200)
        self.bid.refresh_from_db()
        self.assertIsNotNone(self.bid.admin_confirmed)
        self.assertEqual(Decimal("130"), self.bid.items.get().amount_1)

    def test_admin_confirmation_only_preserves_existing_pickup(self):
        location = PickupLocationFactory.create()
        self.bid.pickup_location = location
        self.bid.save()
        self.apiClient.force_authenticate(self.admin)
        response = self.apiClient.patch(
            reverse("bidding_rounds:bid_edit", args=[self.round.pk, self.bid.pk]),
            {"admin_confirmed": True},
            format="json",
        )
        self.assertStatusCode(response, 200)
        self.bid.refresh_from_db()
        self.assertEqual(location.pk, self.bid.pickup_location_id)

    def test_admin_explicit_pickup_removal_invalidates_confirmation(self):
        location = PickupLocationFactory.create()
        self.bid.pickup_location = location
        self.bid.save()
        self.apiClient.force_authenticate(self.admin)
        response = self.apiClient.patch(
            reverse("bidding_rounds:bid_edit", args=[self.round.pk, self.bid.pk]),
            {"pickup_location_id": None},
            format="json",
        )
        self.assertStatusCode(response, 200)
        self.bid.refresh_from_db()
        self.assertIsNone(self.bid.pickup_location_id)
        self.assertIsNone(self.bid.admin_confirmed)

    def test_admin_quantity_change_requires_new_confirmation(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_BID_QUANTITY_ENABLED, True)
        self.apiClient.force_authenticate(self.admin)
        response = self.apiClient.patch(
            reverse("bidding_rounds:bid_edit", args=[self.round.pk, self.bid.pk]),
            {"items": [{**self.item, "quantity": 2}]},
            format="json",
        )
        self.assertStatusCode(response, 200)
        self.bid.refresh_from_db()
        self.assertIsNone(self.bid.admin_confirmed)
        self.assertEqual(2, self.bid.items.get().quantity)

    def test_admin_unchanged_items_preserve_confirmation_and_item_identity(self):
        confirmation = self.bid.admin_confirmed
        item_id = self.bid.items.get().pk
        self.apiClient.force_authenticate(self.admin)
        response = self.apiClient.patch(
            reverse("bidding_rounds:bid_edit", args=[self.round.pk, self.bid.pk]),
            {"items": [{**self.item, "amount_1": "80.00"}]},
            format="json",
        )
        self.assertStatusCode(response, 200)
        self.bid.refresh_from_db()
        self.assertEqual(confirmation, self.bid.admin_confirmed)
        self.assertEqual(item_id, self.bid.items.get().pk)
