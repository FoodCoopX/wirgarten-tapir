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

from tapir.bestell_wizard.services.questionnaire_source_service import (
    QuestionnaireSourceService,
)
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_COMPANY
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.config import (
    SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
)
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
    QuestionaireTrafficSourceOption,
    QuestionaireTrafficSourceResponse,
    OrderFeedback,
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
    PickupLocationCapabilityFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.wirgarten.triggers.onboarding_trigger import OnboardingTrigger


class TestBestellWizardConfirmOrderApiViewPost(TapirIntegrationTest):
    CONTRACT_START_DATE = datetime.date(year=2027, month=6, day=28)
    CONTRACT_START_DATE_FUTURE = datetime.date(year=2028, month=1, day=3)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        configure_mail_module()

        cls.product_1, cls.product_2, cls.product_3 = ProductFactory.create_batch(
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
        # Making sure the source objects are created in the DB
        QuestionnaireSourceService.get_questionnaire_source_choices(cache={})

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(self, datetime.datetime(year=2027, month=6, day=27))

    @patch.object(OnboardingTrigger, "on_subscription_updated", autospec=True)
    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_orderIsValid_memberAndContractGetCreated(
        self, mock_fire_action: Mock, mock_on_subscription_updated: Mock
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
        self.assert_solidarity_contribution_created_correctly(
            member_id=Member.objects.get().id,
            amount_as_string="12.70",
            growing_period=self.growing_period,
        )

        mock_fire_action.assert_called_once()
        self.assert_mail_event_has_been_triggered(
            mock_fire_action=mock_fire_action,
            key=Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION,
        )
        self.assertEqual(2, mock_on_subscription_updated.call_count)

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
        self.assertFalse(SolidarityContribution.objects.exists())

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
        self.assertFalse(SolidarityContribution.objects.exists())

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
        self.assertFalse(SolidarityContribution.objects.exists())

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
        self.assertFalse(SolidarityContribution.objects.exists())

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
        self.assertFalse(SolidarityContribution.objects.exists())

        mock_fire_action.assert_called_once()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_waitingListEntryWithFeedback_feedbackGetsLinkedToWaitingListEntry(
        self, mock_fire_action: Mock
    ):
        feedback_text = "Would love to join as soon as there's capacity!"
        data = self.build_valid_post_data_for_a_waiting_list_entry()
        data["feedback"] = feedback_text

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order should have been confirmed, error: {response_content['error']}",
        )
        self.assertFalse(Member.objects.exists())
        self.assertEqual(1, WaitingListEntry.objects.count())
        self.assertEqual(1, OrderFeedback.objects.count())

        feedback = OrderFeedback.objects.get()
        self.assertEqual(feedback_text, feedback.feedback_text)
        self.assertIsNone(feedback.member)
        self.assertEqual(WaitingListEntry.objects.get(), feedback.waiting_list_entry)

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
        self.assertFalse(SolidarityContribution.objects.exists())

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

        self.assert_solidarity_contribution_created_correctly(
            member_id=Member.objects.get().id,
            amount_as_string="12.70",
            growing_period=self.growing_period,
        )

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
        self.assert_solidarity_contribution_created_correctly(
            member_id=member.id,
            amount_as_string="12.70",
            growing_period=self.growing_period,
        )

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
        self.assert_solidarity_contribution_created_correctly(
            member_id=member.id,
            amount_as_string="12.70",
            growing_period=self.growing_period,
        )

        self.assertFalse(WaitingListEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_investingMemberWithoutCurrentGrowingPeriod_solidarityContributionStartsAtMembershipStart(
        self, mock_fire_action: Mock
    ):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["shopping_cart_order"] = {}
        data["become_member_now"] = True
        data["pickup_location_ids"] = []
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_GROWING_PERIOD_CHOICE_DAYS_BEFORE
        ).update(value=300)
        data["growing_period_id"] = self.growing_period_future.id
        self.growing_period.delete()

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
        self.assert_solidarity_contribution_created_correctly(
            member_id=member.id,
            amount_as_string="12.70",
            growing_period=self.growing_period,
        )

        self.assertFalse(WaitingListEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_investingMemberWithSolidarityContribution_cancellationPolicyIsRequired(
        self, mock_fire_action: Mock
    ):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["shopping_cart_order"] = {}
        data["become_member_now"] = True
        data["pickup_location_ids"] = []
        data["cancellation_policy_read"] = False

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertIn(
            "Die Widerrufsbelehrung muss akzeptiert sein",
            response_content["error"],
        )
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())
        self.assertFalse(SolidarityContribution.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_investingMemberWithoutSolidarityContribution_cancellationPolicyNotRequired(
        self, mock_fire_action: Mock
    ):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["shopping_cart_order"] = {}
        data["become_member_now"] = True
        data["pickup_location_ids"] = []
        data["cancellation_policy_read"] = False
        data["solidarity_contribution"] = 0

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
        self.assertFalse(SolidarityContribution.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())

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
        self.assert_solidarity_contribution_created_correctly(
            member_id=Member.objects.get().id,
            amount_as_string="12.70",
            growing_period=self.growing_period,
        )

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
        self.assert_solidarity_contribution_created_correctly(
            member_id=Member.objects.get().id,
            amount_as_string="12.70",
            growing_period=self.growing_period_future,
        )

        mock_fire_action.assert_called_once()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_severalPickupLocationPickedIncludingAValidOne_memberAndContractAndWaitingListEntryCreated(
        self, mock_fire_action: Mock
    ):
        post_data = self.build_valid_post_data_for_an_order_without_waiting_list()
        post_data["pickup_location_ids"] = [
            self.pickup_location_3.id,
            self.pickup_location_1.id,
            self.pickup_location_2.id,
        ]

        PickupLocationCapabilityFactory.create(
            pickup_location=self.pickup_location_3,
            max_capacity=0,
            product_type=self.product_1.type,
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=self.pickup_location_2,
            max_capacity=0,
            product_type=self.product_1.type,
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=self.pickup_location_1,
            max_capacity=100,
            product_type=self.product_1.type,
        )

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
            mock_fire_action, is_student=False, growing_period=self.growing_period
        )
        self.assertEqual(1, WaitingListEntry.objects.count())

        self.assert_waiting_list_entry_is_correct(
            shopping_cart_waiting_list={},
            pickup_location_wishes=[self.pickup_location_3, self.pickup_location_2],
            mock_fire_action=mock_fire_action,
        )
        self.assert_solidarity_contribution_created_correctly(
            member_id=Member.objects.get().id,
            amount_as_string="12.70",
            growing_period=self.growing_period,
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_severalPickupLocationPickedWithNoneValid_nothingCreated(
        self, mock_fire_action: Mock
    ):
        post_data = self.build_valid_post_data_for_an_order_without_waiting_list()
        post_data["pickup_location_ids"] = [
            self.pickup_location_3.id,
            self.pickup_location_1.id,
            self.pickup_location_2.id,
        ]

        PickupLocationCapabilityFactory.create(
            pickup_location=self.pickup_location_3,
            max_capacity=0.5,
            product_type=self.product_1.type,
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=self.pickup_location_2,
            max_capacity=0.5,
            product_type=self.product_1.type,
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=self.pickup_location_1,
            max_capacity=0.5,
            product_type=self.product_1.type,
        )

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertFalse(
            response_content["order_confirmed"],
        )
        self.assertEqual(
            "Keine der ausgewählte Verteilstationen hat genug Kapazität",
            response_content["error"],
        )
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())
        self.assertFalse(SolidarityContribution.objects.exists())
        mock_fire_action.assert_not_called()

    def test_post_solidarityContributionIsTooLow_returnOrderNotConfirmedAndDontCreateMember(
        self,
    ):
        post_data = self.build_valid_post_data_for_an_order_without_waiting_list()
        post_data["solidarity_contribution"] = -1
        TapirParameter.objects.filter(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED
        ).update(value=SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE)

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertIn(
            "Solidarbeitrag ungültig oder zu niedrig",
            response_content["error"],
        )
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())
        self.assertFalse(SolidarityContribution.objects.exists())

    def test_post_pickupLocationIsDonationLocation_returnOrderNotConfirmedAndDontCreateMember(
        self,
    ):
        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        TapirParameter.objects.filter(
            key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION
        ).update(value=data["pickup_location_ids"][0])
        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertIn(
            "Dieser Abholort kann nicht ausgewählt werden (Das ist die Spende-Sonder-Ort).",
            response_content["error"],
        )
        self.assertFalse(Member.objects.exists())
        self.assertFalse(WaitingListEntry.objects.exists())
        self.assertFalse(SolidarityContribution.objects.exists())

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
            "distribution_channels": [],
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
            "distribution_channels": list(
                QuestionaireTrafficSourceOption.objects.filter(
                    name__in=["Zeitung", "Suchmaschine"]
                ).values_list("id", flat=True)
            ),
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
            "account_owner": "",
            "iban": "",
        }

    @classmethod
    def build_valid_personal_data_order(cls):
        data = cls.build_valid_personal_data_waiting_list()
        data.update(
            {
                "account_owner": "John S. Doe",
                "iban": "NL37RABO2067756052",
            }
        )
        return data

    def assert_personal_data_is_valid_waiting_list(
        self, waiting_list_entry: WaitingListEntry
    ):
        for field, value in self.build_valid_personal_data_waiting_list().items():
            if field in ["account_owner", "iban"]:
                continue
            self.assertEqual(value, getattr(waiting_list_entry, field))

    def assert_personal_data_is_valid_member(self, member: Member):
        for field, value in self.build_valid_personal_data_order().items():
            self.assertEqual(value, getattr(member, field))

    def assert_order_applied_correctly(
        self, mock_fire_action: Mock, is_student: bool, growing_period: GrowingPeriod
    ):
        self.assertEqual(1, Member.objects.count())
        member = Member.objects.get()
        self.assert_personal_data_is_valid_member(member)

        self.assertEqual(2, Subscription.objects.count())

        if growing_period == self.growing_period:
            contract_start_date = self.CONTRACT_START_DATE
        else:
            contract_start_date = self.CONTRACT_START_DATE_FUTURE

        subscription_1 = Subscription.objects.get(member=member, product=self.product_1)
        self.assertEqual(1, subscription_1.quantity)
        self.assertEqual(growing_period, subscription_1.period)
        self.assertEqual(contract_start_date, subscription_1.start_date)
        self.assertEqual(growing_period.end_date, subscription_1.end_date)

        subscription_2 = Subscription.objects.get(member=member, product=self.product_2)
        self.assertEqual(2, subscription_2.quantity)
        self.assertEqual(growing_period, subscription_2.period)
        self.assertEqual(contract_start_date, subscription_2.start_date)
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
            MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=self.now.date()
            ),
        )

        self.assert_mail_event_has_been_triggered(
            mock_fire_action, key=Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION
        )

        self.assertEqual(1, QuestionaireTrafficSourceResponse.objects.count())
        response = QuestionaireTrafficSourceResponse.objects.get()
        self.assertEqual(
            {"Zeitung", "Suchmaschine"},
            set(response.sources.values_list("name", flat=True)),
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

    def assert_solidarity_contribution_created_correctly(
        self, member_id: str, amount_as_string: str, growing_period: GrowingPeriod
    ):
        self.assertEqual(1, SolidarityContribution.objects.count())
        solidarity_contribution = SolidarityContribution.objects.get()
        self.assertEqual(member_id, solidarity_contribution.member_id)
        self.assertEqual(Decimal(amount_as_string), solidarity_contribution.amount)
        if growing_period == self.growing_period:
            contract_start_date = self.CONTRACT_START_DATE
        else:
            contract_start_date = self.CONTRACT_START_DATE_FUTURE
        self.assertEqual(
            contract_start_date,
            solidarity_contribution.start_date,
        )
        self.assertEqual(growing_period.end_date, solidarity_contribution.end_date)

    @patch.object(OnboardingTrigger, "on_subscription_updated", autospec=True)
    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_withFeedback_feedbackGetsSaved(
        self, mock_fire_action: Mock, mock_on_subscription_updated: Mock
    ):
        feedback_text = "Great service, love the organic vegetables!"
        post_data = self.build_valid_post_data_for_an_order_without_waiting_list()
        post_data["feedback"] = feedback_text

        response = self.client.post(
            reverse("bestell_wizard:bestell_wizard_confirm_order"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])

        self.assertEqual(1, OrderFeedback.objects.count())
        self.assertEqual(1, Member.objects.count())
        member = Member.objects.get()
        feedback = OrderFeedback.objects.get()
        self.assertEqual(feedback_text, feedback.feedback_text)
        self.assertEqual(member, feedback.member)
        self.assertIsNone(feedback.waiting_list_entry)

    @patch.object(OnboardingTrigger, "on_subscription_updated", autospec=True)
    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_withoutFeedback_noFeedbackCreated(
        self, mock_fire_action: Mock, mock_on_subscription_updated: Mock
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
        self.assertTrue(response_content["order_confirmed"])

        self.assertEqual(0, OrderFeedback.objects.count())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_waitingListEntryAndOrganizationTypeCompany_createsWaitingListEntryButNoMember(
        self, mock_fire_action: Mock
    ):
        # This is a regression test for #1101 https://github.com/FoodCoopX/wirgarten-tapir/issues/1101
        # When boing through the order wizard with all products on waiting list but becoming a member now, an error was sent from
        # tapir.wirgarten.service.member.send_product_order_confirmation
        # The problem was that the member got created: on companies there are no shares,
        # there is no reason to create the member if the entire order is on waiting list

        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_COMPANY)

        data = self.build_valid_post_data_for_an_order_without_waiting_list()
        data["shopping_cart_order"] = {}
        data["shopping_cart_waiting_list"] = {self.product_1.id: 2}
        data["become_member_now"] = True
        ProductCapacity.objects.update(capacity=1)

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
        self.assertFalse(Subscription.objects.exists())
        self.assert_waiting_list_entry_is_correct(
            shopping_cart_waiting_list=data["shopping_cart_waiting_list"],
            pickup_location_wishes=data["pickup_location_ids"],
            mock_fire_action=mock_fire_action,
        )
