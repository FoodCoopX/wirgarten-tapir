import datetime
import json
from decimal import Decimal
from typing import Any
from unittest.mock import patch, Mock

from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    Subscription,
    CoopShareTransaction,
    WaitingListEntry,
    ProductCapacity,
    WaitingListProductWish,
    WaitingListPickupLocationWish,
    PickupLocation,
    MemberPickupLocation,
    GrowingPeriod,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    PickupLocationFactory,
    GrowingPeriodFactory,
    ProductPriceFactory,
    ProductCapacityFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestBestellWizardConfirmOrderApiViewPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        configure_mail_module()

        (cls.product_1, cls.product_2, cls.product_3) = ProductFactory.create_batch(
            size=3, type__delivery_cycle=WEEKLY[0]
        )
        cls.product_3.type.single_subscription_only = True
        cls.product_3.type.save()

        (
            cls.pickup_location_1,
            cls.pickup_location_2,
            cls.pickup_location_3,
            cls.pickup_location_4,
        ) = PickupLocationFactory.create_batch(size=4)

        ProductPriceFactory.create(product=cls.product_1, size=1)
        ProductPriceFactory.create(product=cls.product_2, size=1.6)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1),
        )
        cls.growing_period_future = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2028, month=1, day=1),
        )
        for growing_period in [cls.growing_period, cls.growing_period_future]:
            ProductCapacityFactory.create(
                product_type=cls.product_1.type, period=growing_period, capacity=10
            )
            ProductCapacityFactory.create(
                product_type=cls.product_2.type, period=growing_period, capacity=10
            )

    def setUp(self) -> None:
        self.now = mock_timezone(self, datetime.datetime(year=2027, month=6, day=27))

        # make sure our test user is not already present in the keycloak db
        client = KeycloakUserManager.get_keycloak_client(cache={})
        user_id = client.get_user_id("john@doe.de")
        if user_id is not None:
            client.delete_user(user_id)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_orderIsValid_memberAndContractGetCreated(
        self, mock_fire_action: Mock
    ):
        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(
                self.build_valid_post_data_for_an_order_without_waiting_list()
            ),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            "Order not confirmed because: " + (response_content["error"] or "no error"),
        )

        self.assert_order_applied_correctly(
            mock_fire_action, is_student=False, growing_period=self.growing_period
        )
        self.assertFalse(WaitingListEntry.objects.exists())

        mock_fire_action.assert_called_once()

    def test_post_requestDataIsInvalid_returns400(self):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        del data["sepa_allowed"]

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 400)
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())

    def test_post_orderValidationFails_returnOrderNotConfirmedAndDontCreateMember(self):
        ProductCapacity.objects.filter(product_type=self.product_2.type).update(
            capacity=2
        )

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(
                self.build_valid_post_data_for_an_order_without_waiting_list()
            ),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertIn(
            "Folgende Produkt-Typen haben nicht genug Kapazität für diese Bestellung:",
            response_content["error"],
        )
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())

    def test_post_memberDataValidationFails_returnOrderNotConfirmedAndDontCreateMember(
        self,
    ):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["personal_data"]["iban"] = "invalid_iban"

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertIn(
            "IBAN",
            response_content["error"],
        )
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())

    def test_post_waitingListValidationFails_returnsOrderNotConfirmedAndDontCreateWaitingListEntry(
        self,
    ):
        data = self.build_valid_post_data_for_a_waiting_list_entry()
        data["number_of_coop_shares"] = 1  # default minimum is 2

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "The given number of coop shares is less than the required minimum.",
            response_content["error"],
        )
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_waitingListEntryIsValid_createsEntry(self, mock_fire_action: Mock):
        data = self.build_valid_post_data_for_a_waiting_list_entry()

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order should have been confirmed, error: {response_content["error"]}",
        )
        self.assertFalse(Member.objects.exists())

        waiting_list_entry = self.assert_waiting_list_entry_is_correct(
            shopping_cart_waiting_list=data["shopping_cart_waiting_list"],
            pickup_location_wishes=[
                self.pickup_location_1,
                self.pickup_location_2,
                self.pickup_location_4,
            ],
            mock_fire_action=mock_fire_action,
        )
        self.assertEqual(2, waiting_list_entry.number_of_coop_shares)
        self.assertIsNone(waiting_list_entry.member_id)
        self.assert_personal_data_is_valid_waiting_list(waiting_list_entry)

        mock_fire_action.assert_called_once()

    def test_post_createNewMemberWithWaitingListEntryButWaitingListEntryIsInvalid_nothingCreated(
        self,
    ):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["shopping_cart_waiting_list"][
            self.product_3.id
        ] = 2  # This product has single_subscription_only = True

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertFalse(
            response_content["order_confirmed"],
        )
        self.assertEqual(
            "Single subscription product ordered more than once",
            response_content["error"],
        )
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_createNewMemberWithOrderAndWaitingListEntry_memberAndWaitingListEntryCreated(
        self, mock_fire_action: Mock
    ):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["shopping_cart_waiting_list"][self.product_3.id] = 1

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"The order should have been confirmed, error: {response_content['error']}",
        )

        member = self.assert_order_applied_correctly(
            mock_fire_action, is_student=False, growing_period=self.growing_period
        )
        waiting_list_entry = self.assert_waiting_list_entry_is_correct(
            shopping_cart_waiting_list=data["shopping_cart_waiting_list"],
            pickup_location_wishes=[],
            mock_fire_action=mock_fire_action,
        )
        self.assertEqual(2, mock_fire_action.call_count)

        self.assertEqual(0, waiting_list_entry.number_of_coop_shares)
        self.assertEqual(member.id, waiting_list_entry.member_id)

        self.assertEqual(1, SolidarityContribution.objects.count())
        solidarity_contribution = SolidarityContribution.objects.get()
        self.assertEqual(member.id, solidarity_contribution.member_id)
        self.assertEqual(Decimal("12.70"), solidarity_contribution.amount)
        self.assertEqual(
            Subscription.objects.first().start_date, solidarity_contribution.start_date
        )
        self.assertEqual(self.growing_period.end_date, solidarity_contribution.end_date)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_waitingListEntryAndBecomeMemberNow_createsEntryAndCreatesMember(
        self, mock_fire_action: Mock
    ):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["shopping_cart_waiting_list"] = data["shopping_cart_order"]
        data["shopping_cart_order"] = {}
        data["become_member_now"] = True
        data["pickup_location_ids"] = [
            self.pickup_location_1.id,
            self.pickup_location_2.id,
            self.pickup_location_4.id,
        ]

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order should have been confirmed, error: {response_content["error"]}",
        )

        self.assertEqual(1, Member.objects.count())
        member = Member.objects.get()
        self.assert_personal_data_is_valid_member(member)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        coop_share_transaction = CoopShareTransaction.objects.get()
        self.assertEqual(member, coop_share_transaction.member)
        self.assertEqual(2, coop_share_transaction.quantity)

        self.assertFalse(Subscription.objects.exists())
        self.assertFalse(MemberPickupLocation.objects.exists())

        self.assertEqual(2, mock_fire_action.call_count)
        self.assert_mail_event_has_been_triggered(
            mock_fire_action, key=Events.REGISTER_MEMBERSHIP_ONLY
        )

        waiting_list_entry = self.assert_waiting_list_entry_is_correct(
            shopping_cart_waiting_list=data["shopping_cart_waiting_list"],
            pickup_location_wishes=[
                self.pickup_location_1,
                self.pickup_location_2,
                self.pickup_location_4,
            ],
            mock_fire_action=mock_fire_action,
        )
        self.assertEqual(0, waiting_list_entry.number_of_coop_shares)
        self.assertEqual(member.id, waiting_list_entry.member_id)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_investingMember_createsMember(self, mock_fire_action: Mock):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["shopping_cart_order"] = {}
        data["become_member_now"] = True
        data["pickup_location_ids"] = []

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order should have been confirmed, error: {response_content["error"]}",
        )

        self.assertEqual(1, Member.objects.count())
        member = Member.objects.get()
        self.assert_personal_data_is_valid_member(member)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        coop_share_transaction = CoopShareTransaction.objects.get()
        self.assertEqual(member, coop_share_transaction.member)
        self.assertEqual(2, coop_share_transaction.quantity)

        self.assertFalse(Subscription.objects.exists())
        self.assertFalse(MemberPickupLocation.objects.exists())

        mock_fire_action.assert_called_once()
        self.assert_mail_event_has_been_triggered(
            mock_fire_action, key=Events.REGISTER_MEMBERSHIP_ONLY
        )

        self.assertFalse(WaitingListEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_investingMemberOnWaitingList_createsWaitingListEntry(
        self, mock_fire_action: Mock
    ):
        data = self.build_valid_post_data_for_a_waiting_list_entry()
        data["shopping_cart_waiting_list"] = {}
        data["pickup_location_ids"] = []
        data["number_of_coop_shares"] = 7

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order should have been confirmed, error: {response_content["error"]}",
        )

        self.assertFalse(Member.objects.exists())

        waiting_list_entry = self.assert_waiting_list_entry_is_correct(
            shopping_cart_waiting_list={},
            pickup_location_wishes=[],
            mock_fire_action=mock_fire_action,
        )
        self.assertEqual(7, waiting_list_entry.number_of_coop_shares)
        self.assertIsNone(waiting_list_entry.member_id)
        self.assert_personal_data_is_valid_waiting_list(waiting_list_entry)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_orderingAsStudent_noCoopShareCreated(self, mock_fire_action: Mock):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["student_status_enabled"] = True
        data["number_of_coop_shares"] = 0
        data["statute_accepted"] = False

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order not confirmed because, error: {response_content['error']}",
        )

        self.assert_order_applied_correctly(
            mock_fire_action, is_student=True, growing_period=self.growing_period
        )
        self.assertFalse(WaitingListEntry.objects.exists())

        mock_fire_action.assert_called_once()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_futureGrowingPeriodPicked_contractGetsCreatedWithCorrectStartDate(
        self, mock_fire_action: Mock
    ):
        post_data = self.build_valid_post_data_for_an_order_without_waiting_list()
        post_data["growing_period_id"] = self.growing_period_future.id
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_GROWING_PERIOD_CHOICE_DAYS_BEFORE
        ).update(value=300)

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            "Order not confirmed because: " + (response_content["error"] or "no error"),
        )

        self.assert_order_applied_correctly(
            mock_fire_action,
            is_student=False,
            growing_period=self.growing_period_future,
        )
        self.assertFalse(WaitingListEntry.objects.exists())

        mock_fire_action.assert_called_once()

    @classmethod
    def build_valid_post_data_for_a_waiting_list_entry(cls) -> dict[str, Any]:
        return {
            "shopping_cart_order": {},
            "shopping_cart_waiting_list": {cls.product_1.id: 1, cls.product_2.id: 2},
            "personal_data": cls.build_valid_personal_data_waiting_list(),
            "sepa_allowed": False,
            "contract_accepted": False,
            "statute_accepted": False,
            "number_of_coop_shares": 2,
            "pickup_location_ids": [
                cls.pickup_location_1.id,
                cls.pickup_location_2.id,
                cls.pickup_location_4.id,
            ],
            "student_status_enabled": False,
            "payment_rhythm": MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            "become_member_now": False,
            "privacy_policy_read": True,
            "cancellation_policy_read": False,
            "growing_period_id": cls.growing_period.id,
            "solidarity_contribution": 0,
        }

    @classmethod
    def build_valid_post_data_for_an_order_without_waiting_list(cls) -> dict[str, Any]:
        return {
            "shopping_cart_order": {cls.product_1.id: 1, cls.product_2.id: 2},
            "shopping_cart_waiting_list": {},
            "personal_data": cls.build_valid_personal_data_order(),
            "sepa_allowed": True,
            "contract_accepted": True,
            "statute_accepted": True,
            "number_of_coop_shares": 2,
            "pickup_location_ids": [cls.pickup_location_1.id],
            "student_status_enabled": False,
            "payment_rhythm": MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            "become_member_now": None,
            "privacy_policy_read": True,
            "cancellation_policy_read": True,
            "growing_period_id": cls.growing_period.id,
            "solidarity_contribution": 12.7,
        }

    @classmethod
    def build_valid_personal_data_waiting_list(cls):
        return {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@doe.de",
            "phone_number": "017628244239",
            "street": "Baker Street 221b",
            "street_2": "2nd floor",
            "postcode": "16321",
            "city": "Berlin",
            "country": "DE",
            "birthdate": datetime.date.today().isoformat(),
            "account_owner": "",
            "iban": "",
        }

    @classmethod
    def build_valid_personal_data_order(cls):
        data = cls.build_valid_personal_data_waiting_list()
        data.update(
            {
                "birthdate": "1990-12-21",
                "account_owner": "John S. Doe",
                "iban": "NL37RABO2067756052",
            }
        )
        return data

    def assert_personal_data_is_valid_waiting_list(
        self, waiting_list_entry: WaitingListEntry
    ):
        for field, value in self.build_valid_personal_data_waiting_list().items():
            if field in ["birthdate", "account_owner", "iban"]:
                continue
            self.assertEqual(value, getattr(waiting_list_entry, field))

    def assert_personal_data_is_valid_member(self, member: Member):
        for field, value in self.build_valid_personal_data_order().items():
            if field == "birthdate":
                value = datetime.date(year=1990, month=12, day=21)
            self.assertEqual(value, getattr(member, field))

    def assert_order_applied_correctly(
        self, mock_fire_action: Mock, is_student: bool, growing_period: GrowingPeriod
    ):
        self.assertEqual(1, Member.objects.count())
        member = Member.objects.get()
        self.assert_personal_data_is_valid_member(member)

        self.assertEqual(2, Subscription.objects.count())

        subscription_1 = Subscription.objects.get(member=member, product=self.product_1)
        self.assertEqual(1, subscription_1.quantity)
        self.assertEqual(growing_period, subscription_1.period)
        self.assertLess(self.now.date(), subscription_1.start_date)
        self.assertGreater(subscription_1.start_date, growing_period.start_date)
        self.assertEqual(growing_period.end_date, subscription_1.end_date)

        subscription_2 = Subscription.objects.get(member=member, product=self.product_2)
        self.assertEqual(2, subscription_2.quantity)
        self.assertEqual(growing_period, subscription_2.period)
        self.assertLess(self.now.date(), subscription_2.start_date)
        self.assertGreater(subscription_2.start_date, growing_period.start_date)
        self.assertEqual(growing_period.end_date, subscription_2.end_date)

        if is_student:
            self.assertFalse(CoopShareTransaction.objects.exists())
            self.assertTrue(member.is_student)
        else:
            self.assertFalse(member.is_student)
            self.assertEqual(1, CoopShareTransaction.objects.count())
            coop_share_transaction = CoopShareTransaction.objects.get()
            self.assertEqual(member, coop_share_transaction.member)
            self.assertEqual(2, coop_share_transaction.quantity)

        self.assertEqual(
            MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=subscription_1.start_date, cache={}
            ),
        )

        self.assertEqual(
            self.pickup_location_1.id,
            MemberPickupLocationService.get_member_pickup_location_id(
                member=member, reference_date=self.now.date()
            ),
        )

        self.assert_mail_event_has_been_triggered(
            mock_fire_action, key=Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION
        )

        return member

    def assert_waiting_list_entry_is_correct(
        self,
        shopping_cart_waiting_list: dict,
        pickup_location_wishes: list[PickupLocation],
        mock_fire_action: Mock,
    ):
        self.assertEqual(1, WaitingListEntry.objects.count())
        waiting_list_entry = WaitingListEntry.objects.get()
        self.assertEqual(self.now, waiting_list_entry.privacy_consent)

        self.assertEqual(
            len(pickup_location_wishes), WaitingListPickupLocationWish.objects.count()
        )
        for index, pickup_location in enumerate(pickup_location_wishes):
            self.assertEqual(
                1,
                WaitingListPickupLocationWish.objects.filter(
                    waiting_list_entry=waiting_list_entry,
                    pickup_location=pickup_location,
                    priority=index + 1,
                ).count(),
            )

        self.assertEqual(
            len(shopping_cart_waiting_list), WaitingListProductWish.objects.count()
        )
        for product_id, quantity in shopping_cart_waiting_list.items():
            self.assertEqual(
                1,
                WaitingListProductWish.objects.filter(
                    waiting_list_entry=waiting_list_entry,
                    product_id=product_id,
                    quantity=quantity,
                ).count(),
            )

        self.assert_mail_event_has_been_triggered(
            mock_fire_action, key=Events.CONFIRMATION_REGISTRATION_IN_WAITING_LIST
        )

        return waiting_list_entry

    def assert_mail_event_has_been_triggered(self, mock_fire_action: Mock, key: str):
        mock_fire_action.assert_called()
        for call in mock_fire_action.mock_calls:
            trigger_data: TransactionalTriggerData = call[1][0]
            if trigger_data.key == key:
                return

        self.fail(
            f"Expected trigger ({key}) not found in {mock_fire_action.mock_calls}"
        )
