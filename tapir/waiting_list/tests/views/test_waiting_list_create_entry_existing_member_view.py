import datetime
import json
from unittest.mock import patch, Mock

from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import TransactionalTriggerData

from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    WaitingListEntry,
    WaitingListPickupLocationWish,
    WaitingListProductWish,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestWaitingListCreateEntryExistingMemberView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, datetime.datetime(year=2025, month=6, day=15))
        self.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        self.product = ProductFactory.create()
        self.pickup_location = PickupLocationFactory.create()

    def build_request_data(self, member_id: str):
        return {
            "member_id": member_id,
            "shopping_cart": {self.product.id: 2},
            "pickup_location_ids": [self.pickup_location.id],
        }

    def post_request(self, data: dict):
        return self.client.post(
            reverse("waiting_list:waiting_list_create_entry_existing_member"),
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_post_anonymousUser_returns403(self):
        member = MemberFactory.create()

        response = self.post_request(self.build_request_data(member.id))

        self.assertEqual(403, response.status_code)
        self.assertEqual(0, WaitingListEntry.objects.count())

    def test_post_loggedInAsDifferentNormalMember_returns403(self):
        target_member = MemberFactory.create()
        logged_in_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_member)

        response = self.post_request(self.build_request_data(target_member.id))

        self.assertEqual(403, response.status_code)
        self.assertEqual(0, WaitingListEntry.objects.count())

    def test_post_memberDoesNotExist_returns404(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        response = self.post_request(self.build_request_data("does-not-exist"))

        self.assertEqual(404, response.status_code)
        self.assertEqual(0, WaitingListEntry.objects.count())

    @patch("tapir_mail.triggers.transactional_trigger.TransactionalTrigger.fire_action")
    def test_post_memberAlreadyHasWaitingListEntry_returnsOrderNotConfirmed(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create(is_superuser=False)
        WaitingListEntryFactory.create(member=member)
        self.client.force_login(member)

        response = self.post_request(self.build_request_data(member.id))

        self.assertEqual(200, response.status_code)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Es gibt schon einen Warteliste-Eintrag für dieses Mitglied.",
            response_content["error"],
        )
        self.assertEqual(1, WaitingListEntry.objects.count())
        mock_fire_action.assert_not_called()

    @patch("tapir_mail.triggers.transactional_trigger.TransactionalTrigger.fire_action")
    def test_post_loggedInAsSelf_createsEntryAndSendsConfirmationMail(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.post_request(self.build_request_data(member.id))

        self.assertEqual(200, response.status_code)
        response_content = response.json()
        self.assert_order_confirmed(response_content)

        self.assertEqual(1, WaitingListEntry.objects.count())
        entry = WaitingListEntry.objects.get()
        self.assertEqual(member, entry.member)
        self.assertEqual(0, entry.number_of_coop_shares)

        self.assertEqual(1, WaitingListProductWish.objects.count())
        product_wish = WaitingListProductWish.objects.get()
        self.assertEqual(entry, product_wish.waiting_list_entry)
        self.assertEqual(self.product, product_wish.product)
        self.assertEqual(2, product_wish.quantity)

        self.assertEqual(1, WaitingListPickupLocationWish.objects.count())
        pickup_location_wish = WaitingListPickupLocationWish.objects.get()
        self.assertEqual(entry, pickup_location_wish.waiting_list_entry)
        self.assertEqual(self.pickup_location, pickup_location_wish.pickup_location)
        self.assertEqual(1, pickup_location_wish.priority)

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args.kwargs[
            "trigger_data"
        ]
        self.assertEqual(
            Events.CONFIRMATION_REGISTRATION_IN_WAITING_LIST, trigger_data.key
        )
        self.assertEqual(member.id, trigger_data.recipient_id_in_base_queryset)
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual(
            {
                "contract_list": f"<ul><li>{self.product.name} x 2</li></ul>",
                "pickup_location_list": f"<ol><li>{self.pickup_location.name}</li></ol>",
                "desired_start_date": "so früh wie möglich",
            },
            trigger_data.token_data,
        )

    @patch("tapir_mail.triggers.transactional_trigger.TransactionalTrigger.fire_action")
    def test_post_noGrowingPeriodCoveringToday_stillCreatesEntry(
        self, mock_fire_action: Mock
    ):
        # Regression test for #1149 https://github.com/FoodCoopX/wirgarten-tapir/issues/1149
        self.growing_period.delete()
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.post_request(self.build_request_data(member.id))

        self.assertEqual(200, response.status_code)
        response_content = response.json()
        self.assert_order_confirmed(response_content)
        self.assertEqual(1, WaitingListEntry.objects.count())
        mock_fire_action.assert_called_once()

    @patch("tapir_mail.triggers.transactional_trigger.TransactionalTrigger.fire_action")
    def test_post_loggedInAsAdminForAnotherMember_createsEntry(
        self, mock_fire_action: Mock
    ):
        target_member = MemberFactory.create()
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        response = self.post_request(self.build_request_data(target_member.id))

        self.assertEqual(200, response.status_code)
        response_content = response.json()
        self.assert_order_confirmed(response_content)

        self.assertEqual(1, WaitingListEntry.objects.count())
        entry = WaitingListEntry.objects.get()
        self.assertEqual(target_member, entry.member)
        mock_fire_action.assert_called_once()
