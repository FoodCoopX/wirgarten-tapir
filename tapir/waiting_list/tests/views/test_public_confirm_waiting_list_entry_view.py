import datetime
import json
import uuid
from decimal import Decimal
from unittest.mock import patch, Mock

from django.urls import reverse
from keycloak import KeycloakPutError
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTriggerData,
    TransactionalTrigger,
)

from tapir.accounts.services.email_verification_service import EmailVerificationService
from tapir.accounts.services.keycloak_user_delete_service import (
    KeycloakUserDeleteService,
)
from tapir.associations.mail_tokens import ASSOCIATION_DEPOSIT_MAIL_TOKENS
from tapir.associations.models import AssociationDepositAccount
from tapir.associations.models import AssociationMembership
from tapir.associations.tests.factories import AssociationMembershipTypeFactory
from tapir.core.config import (
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_COMPANY,
    LEGAL_STATUS_ASSOCIATION,
)
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.constants import WEEKLY, NO_DELIVERY
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    CoopShareTransaction,
    Member,
    OrderFeedback,
    WaitingListEntry,
    WaitingListProductWish,
    Subscription,
    WaitingListPickupLocationWish,
    PickupLocationOpeningTime,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    GrowingPeriodFactory,
    ProductFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestPublicConfirmWaitingListEntryView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.pickup_location = PickupLocationFactory.create()

    def test_post_waitingListEntryWithFeedback_feedbackGetsTransferredToMember(self):
        feedback_text = "Looking forward to joining soon!"

        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(),
            member=None,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        OrderFeedback.objects.create(
            waiting_list_entry=entry, feedback_text=feedback_text
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))

        self.assertEqual(1, OrderFeedback.objects.count())
        self.assertIsNone(OrderFeedback.objects.get().member)
        self.assertEqual(entry, OrderFeedback.objects.get().waiting_list_entry)

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": None,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertEqual(200, response.status_code)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order not confirmed. Error: {response_content.get('error')}",
        )

        self.assertEqual(1, Member.objects.count())
        member = Member.objects.get()
        self.assertEqual("John", member.first_name)
        self.assertEqual("Doe", member.last_name)

        self.assertEqual(1, OrderFeedback.objects.count())
        feedback = OrderFeedback.objects.get()
        self.assertEqual(feedback_text, feedback.feedback_text)
        self.assertEqual(member, feedback.member)
        self.assertIsNone(feedback.waiting_list_entry)

        self.assertEqual(0, WaitingListEntry.objects.count())

    @patch(
        "tapir_mail.triggers.transactional_trigger.TransactionalTrigger.fire_action",
        autospec=True,
    )
    def test_post_waitingListEntryWithoutStartDateAndNoGrowingPeriodOnCurrentStartDate_startsContractOnFollowingGrowingPeriod(
        self, mock_fire_action: Mock
    ):
        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(),
            desired_start_date=None,
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=6, day=1))
        product = ProductFactory.create()
        ProductPriceFactory.create(
            product=product,
            valid_from=datetime.date(year=1990, month=1, day=1),
            price=Decimal("10.00"),
        )
        WaitingListProductWish.objects.create(
            product=product, waiting_list_entry=entry, quantity=2
        )

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": None,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertEqual(200, response.status_code)
        response_content = response.json()
        self.assert_order_confirmed(response_content)

        self.assertEqual(1, Member.objects.count())
        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(0, WaitingListEntry.objects.count())

        subscription = Subscription.objects.get()
        self.assertEqual(
            datetime.date(year=1997, month=6, day=2), subscription.start_date
        )
        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].kwargs["trigger_data"]
        self.assertEqual(Events.WAITING_LIST_ORDER_CONFIRMATION, trigger_data.key)

    def test_post_legalStatusIsNotCooperative_noCoopSharesArePurchased(self):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COMPANY
        )

        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(),
            member=None,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": None,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response.json())
        self.assertEqual(1, Member.objects.count())
        self.assertFalse(CoopShareTransaction.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_waitingListEntryWithDeliveredProduct_mailConfirmationGetsSentWithCorrectDates(
        self, mock_fire_action: Mock
    ):
        # Regression test for infra#59

        self._set_parameter(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, value=1
        )  # Date limit Tuesday
        self._set_parameter(
            key=ParameterKeys.DELIVERY_DAY, value=3
        )  # Deliveries on Thursday
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )

        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(),
            member=None,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        product = ProductFactory.create(
            type__delivery_cycle=WEEKLY[0], name="M", type__name="Basket"
        )
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry,
            product=product,
            quantity=1,
        )
        ProductPriceFactory.create(
            product=product,
            valid_from=datetime.date(year=2026, month=1, day=1),
            price=Decimal("10.00"),
        )
        pickup_location = PickupLocationFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=pickup_location, priority=1
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=pickup_location,
            day_of_week=6,
            open_time=datetime.time(hour=10),
            close_time=datetime.time(hour=18),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=pickup_location,
            day_of_week=3,
            open_time=datetime.time(hour=10),
            close_time=datetime.time(hour=18),
        )

        mock_timezone(test=self, now=datetime.datetime(year=2026, month=5, day=12))
        GrowingPeriodFactory.create(start_date=datetime.date(year=2026, month=1, day=1))

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 12,
            "association_membership_type_id": None,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=confirm_data,
            content_type="application/json",
        )

        self.assertEqual(200, response.status_code)
        self.assert_order_confirmed(response.json())

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].kwargs["trigger_data"]
        self.assertEqual(Events.WAITING_LIST_ORDER_CONFIRMATION, trigger_data.key)
        self.assertEqual(
            {
                "contract_start_date": "11.05.2026",
                "contract_end_date": "31.12.2026",
                "contract_list": (
                    '<ul style="margin:0;padding:0 0 0 1.2em;">'
                    '<li style="margin:0;">1 × M Basket  (11.05.2026 - 31.12.2026): 10,00 € / Monat</li></ul>'
                ),
                "membership_start_date": "07.06.2026",
                "membership_monthly_price": "0,00",
                "first_pickup_date": "14.05.2026",
                "number_of_coop_shares": 2,
                "price_of_a_coop_share": "50,00",
                "total_cost": "100,00",
                "coop_shares_payment_method": "einmalig",
                "solidarity_contribution_amount": "12,00",
                "solidarity_contribution_start_date": "11.05.2026",
                "monthly_total": "22,00",
                "payment_rhythm": "Halbjährlich",
            }
            | dict.fromkeys(ASSOCIATION_DEPOSIT_MAIL_TOKENS.values(), ""),
            trigger_data.token_data,
        )

    def test_post_legalStatusIsAssociation_associationMembershipCreated(self):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )

        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(),
            member=None,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))
        membership_type = AssociationMembershipTypeFactory.create()

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": membership_type.id,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response.json())
        self.assertEqual(1, Member.objects.count())
        self.assertFalse(CoopShareTransaction.objects.exists())

        self.assertEqual(1, AssociationMembership.objects.count())
        membership = AssociationMembership.objects.get()
        self.assertEqual(membership_type, membership.type)

    def test_post_memberNumbersAreAssignedOnRegistration_memberGetsCreatedWithNumber(
        self,
    ):
        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(),
            member=None,
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))
        self._set_parameter(
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, value=False
        )

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": None,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response.json())

        member = Member.objects.get()
        self.assertIsNotNone(member.member_no)

    def test_post_mandateReferenceRequiresAMemberNumber_mandateReferenceCreated(
        self,
    ):
        # This is a regression test for a bug reported in issue #884 in this comment: https://github.com/FoodCoopX/wirgarten-tapir/issues/884#issuecomment-5176735897
        # where the pattern for the mandate reference uses the member number, but at the time of the creation of the mandate reference,
        # the member didn't have a number yet.

        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(),
            member=None,
        )
        product = ProductFactory.create()
        ProductPriceFactory.create(
            product=product,
            valid_from=datetime.date(year=1990, month=1, day=1),
            price=Decimal("10.00"),
        )
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, quantity=1, product=product
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))
        self._set_parameter(
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, value=False
        )
        self._set_parameter(
            key=ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN,
            value="{mitgliedsnummer_ohne_prefix}",
        )

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": None,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response.json())

    @patch.object(KeycloakUserDeleteService, "delete_user_if_exists", autospec=True)
    @patch.object(EmailVerificationService, "send_verification_email", autospec=True)
    def test_post_sendingOfEmailVerificationFails_changesRolledBackAndMemberDeletedFromKeycloak(
        self,
        mock_send_verification_email: Mock,
        mock_delete_user_if_exists: Mock,
    ):
        # If sending the mail verification fails, an exception will be raised by the keycloak client.
        # This will cause the transaction to rollback, the member will not be in the Tapir DB
        # However, since the mail is sent after the user is created in Keycloak, the user would still exist in keycloak.
        # This test makes sure the user is deleted in keycloak too.

        mock_send_verification_email.side_effect = KeycloakPutError()

        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(),
            member=None,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": None,
        }
        with self.assertRaises(KeycloakPutError):
            self.client.post(
                reverse("waiting_list:public_confirm_waiting_list_entry"),
                data=json.dumps(confirm_data),
                content_type="application/json",
            )

        self.assertFalse(Member.objects.exists())

        mock_send_verification_email.assert_called_once()
        mock_delete_user_if_exists.assert_called_once()
        self.assertEqual(
            mock_send_verification_email.call_args.kwargs["user"],
            mock_delete_user_if_exists.call_args.kwargs["user"],
        )

    def test_post_entryWithPseudonym_memberCreatedWithPseudonym(self):
        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(), member=None, pseudonym="Brotfan"
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": None,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertEqual(200, response.status_code)
        response_content = response.json()
        self.assertTrue(
            response_content["order_confirmed"],
            f"Order not confirmed. Error: {response_content.get('error')}",
        )
        self.assertEqual("Brotfan", Member.objects.get().pseudonym)

    def test_post_emptyIban_errorMessageHasNoPlaceholders(self):
        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(), member=None
        )
        mock_timezone(test=self, now=datetime.datetime(year=1997, month=3, day=30))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))

        confirm_data = {
            "entry_id": str(entry.id),
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "John Doe",
            "iban": "",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 2,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": None,
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertEqual(200, response.status_code)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertNotIn("%(", response_content["error"])

    def prepare_deposit_confirmation(self, with_product=False):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        entry = WaitingListEntryFactory(
            confirmation_link_key=uuid.uuid4(),
            member=None,
            email="deposit-waiting@example.test",
        )
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        GrowingPeriodFactory(
            start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2027, 12, 31)
        )
        if with_product:
            product = ProductFactory(type__delivery_cycle=NO_DELIVERY[0])
            ProductPriceFactory(
                product=product, price=30, valid_from=datetime.date(2026, 1, 1)
            )
            WaitingListProductWish.objects.create(
                waiting_list_entry=entry, product=product, quantity=1
            )
        membership_type = AssociationMembershipTypeFactory()
        return entry, {
            "entry_id": entry.pk,
            "link_key": str(entry.confirmation_link_key),
            "account_owner": "Test Mitglied",
            "iban": "NL35ABNA7806242643",
            "sepa_allowed": True,
            "contract_accepted": True,
            "number_of_coop_shares": 0,
            "payment_rhythm": "semiannually",
            "solidarity_contribution": 0,
            "association_membership_type_id": membership_type.pk,
        }

    @patch.object(TransactionalTrigger, "fire_all_released_configs", autospec=True)
    def test_new_waiting_list_member_explicitly_agrees_deposit(self, mock_dispatch):
        entry, data = self.prepare_deposit_confirmation(with_product=True)
        data["association_deposit_amount"] = "200"
        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code, response.content)
        self.assert_order_confirmed(response.json())
        account = AssociationDepositAccount.objects.get()
        self.assertEqual(200, account.agreed_amount)
        self.assertEqual(200, account.payments.get().amount)

        event = next(
            call.args[0]
            for call in mock_dispatch.call_args_list
            if call.args[0].key == Events.WAITING_LIST_ORDER_CONFIRMATION
        )
        self.assertEqual("200,00", event.token_data["association_deposit_amount"])
        self.assertEqual(
            1, event.token_data["association_deposit_payment_plan"].count("(offen)")
        )

    def test_missing_waiting_list_deposit_keeps_entry_without_member_or_debit(self):
        entry, data = self.prepare_deposit_confirmation()
        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertFalse(response.json()["order_confirmed"])
        self.assertIn("Vereinseinlage", response.json()["error"])
        self.assertTrue(type(entry).objects.filter(pk=entry.pk).exists())
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Member.objects.exists())

    def test_zero_quantity_waiting_wish_does_not_require_supporting_deposit(self):
        entry, data = self.prepare_deposit_confirmation()
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_REQUIRED, False
        )
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=ProductFactory(), quantity=0
        )
        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code, response.content)
        self.assert_order_confirmed(response.json())
        self.assertFalse(AssociationDepositAccount.objects.exists())

    def test_positive_waiting_wish_requires_deposit_even_if_supporters_are_exempt(self):
        entry, data = self.prepare_deposit_confirmation()
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_REQUIRED, False
        )
        product = ProductFactory()
        ProductPriceFactory(
            product=product, valid_from=datetime.date(2026, 1, 1), price=30
        )
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=product, quantity=1
        )
        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertFalse(response.json()["order_confirmed"])
        self.assertIn("Vereinseinlage", response.json()["error"])
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Member.objects.exists())

    @patch.object(TransactionalTrigger, "fire_all_released_configs", autospec=True)
    def test_new_waiting_list_member_can_select_standard_rates(self, mock_dispatch):
        entry, data = self.prepare_deposit_confirmation(with_product=True)
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True)
        data.update(
            association_deposit_amount="200",
            association_deposit_payment_option="standard_instalments",
            association_deposit_expected_instalments=4,
        )
        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assert_order_confirmed(response.json())
        account = AssociationDepositAccount.objects.get()
        self.assertFalse(account.is_individual_agreement)
        self.assertEqual(
            [Decimal("50")] * 4, list(account.payments.values_list("amount", flat=True))
        )
        self.assertFalse(type(entry).objects.filter(pk=entry.pk).exists())

        event = next(
            call.args[0]
            for call in mock_dispatch.call_args_list
            if call.args[0].key == Events.WAITING_LIST_ORDER_CONFIRMATION
        )
        self.assertEqual("200,00", event.token_data["association_deposit_amount"])
        self.assertEqual(
            4, event.token_data["association_deposit_payment_plan"].count("(offen)")
        )

    @patch.object(TransactionalTrigger, "fire_all_released_configs", autospec=True)
    def test_new_waiting_list_member_hardship_keeps_unknown_agreement_without_payment(
        self,
        mock_dispatch,
    ):
        entry, data = self.prepare_deposit_confirmation(with_product=True)
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        data["association_deposit_payment_option"] = "hardship"
        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assert_order_confirmed(response.json())
        account = AssociationDepositAccount.objects.get()
        self.assertIsNone(account.agreed_amount)
        self.assertIsNone(account.effective_from)
        self.assertIsNotNone(account.hardship_requested_at)
        self.assertFalse(account.payments.exists())
        self.assertFalse(type(entry).objects.filter(pk=entry.pk).exists())
        self.assertEqual(1, AssociationMembership.objects.count())

        event = next(
            call.args[0]
            for call in mock_dispatch.call_args_list
            if call.args[0].key == Events.WAITING_LIST_ORDER_CONFIRMATION
        )
        self.assertEqual(
            "Nicht vereinbart", event.token_data["association_deposit_amount"]
        )
        self.assertEqual(
            0, event.token_data["association_deposit_payment_plan"].count("(offen)")
        )

    def test_invalid_deposit_choices_rejected_before_external_user_creation(self):
        entry, data = self.prepare_deposit_confirmation()
        cases = [
            ("hardship", None, False, False, 4),
            ("hardship", "0", True, False, 4),
            ("hardship", "200", True, False, 4),
            ("standard_instalments", "200", False, False, 4),
            ("standard_instalments", "200", False, True, 0),
            ("standard_instalments", "200", False, True, 121),
            ("standard_instalments", "200", False, True, 6),
            ("standard_instalments", "200", False, True, 10**9),
            ("standard_instalments", "100", False, True, 4),
        ]
        for option, amount, hardship, rates, count in cases:
            with self.subTest(
                option=option, amount=amount, count=count, enabled=(hardship, rates)
            ):
                self._set_parameter(
                    ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, hardship
                )
                self._set_parameter(
                    ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, rates
                )
                self._set_parameter(
                    ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT, str(count)
                )
                data.update(
                    association_deposit_amount=amount,
                    association_deposit_payment_option=option,
                    association_deposit_expected_instalments=(
                        4 if option == "standard_instalments" else None
                    ),
                )
                response = self.client.post(
                    reverse("waiting_list:public_confirm_waiting_list_entry"),
                    data=json.dumps(data),
                    content_type="application/json",
                )
                self.assertEqual(200, response.status_code, response.content)
                self.assertFalse(response.json()["order_confirmed"])
                self.assertTrue(response.json()["error"])
                self.mock_keycloak_client.create_user.assert_not_called()
                self.assertFalse(Member.objects.exists())
                self.assertFalse(AssociationDepositAccount.objects.exists())
                self.assertTrue(type(entry).objects.filter(pk=entry.pk).exists())

    def test_subcent_standard_rates_rejected_before_external_user_creation(self):
        entry, data = self.prepare_deposit_confirmation()
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True)
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, "0.01")
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, "0.01")
        data.update(
            association_deposit_amount="0.01",
            association_deposit_payment_option="standard_instalments",
            association_deposit_expected_instalments=4,
        )
        self.client.raise_request_exception = False
        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.mock_keycloak_client.create_user.assert_not_called()
        self.assertEqual(200, response.status_code, response.content)
        self.assertFalse(response.json()["order_confirmed"])
        self.assertFalse(Member.objects.exists())
        self.assertTrue(type(entry).objects.filter(pk=entry.pk).exists())
