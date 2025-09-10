import datetime
import json
from typing import Any
from unittest.mock import patch, Mock

from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    Subscription,
    CoopShareTransaction,
    WaitingListEntry,
    ProductCapacity,
)
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
    # TODO
    # validation waiting list potential member fails: 400
    # validation waiting list potential member passes: 200, WLE created, member not created
    # validation waiting list existing member fails: 400, member not created
    # validation waiting list existing member passes: 200, member and WLE created
    # waiting list + member now: member created, WLE created
    # investing member, no waiting list: member created

    # DONE
    # serializer invalid: 400
    # order valid: member created, WLE not created
    # order validation fails: 400
    # data new member validation fails: 400

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        configure_mail_module()

        cls.product_1 = ProductFactory.create()
        cls.product_2 = ProductFactory.create()
        cls.pickup_location = PickupLocationFactory.create()
        ProductPriceFactory.create(product=cls.product_1, size=1)
        ProductPriceFactory.create(product=cls.product_2, size=1.6)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        ProductCapacityFactory.create(
            product_type=cls.product_1.type, period=cls.growing_period, capacity=10
        )
        ProductCapacityFactory.create(
            product_type=cls.product_2.type, period=cls.growing_period, capacity=10
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

        self.assertEqual(1, Member.objects.count())
        member = Member.objects.get()
        self.assertEqual("John", member.first_name)
        self.assertEqual("Doe", member.last_name)
        self.assertEqual("john@doe.de", member.email)
        self.assertEqual("017628244239", member.phone_number)
        self.assertEqual("Baker Street 221b", member.street)
        self.assertEqual("2nd floor", member.street_2)
        self.assertEqual("16321", member.postcode)
        self.assertEqual("Berlin", member.city)
        self.assertEqual("DE", member.country)
        self.assertEqual(datetime.date(year=1990, month=12, day=21), member.birthdate)
        self.assertEqual("John S. Doe", member.account_owner)
        self.assertEqual("NL37RABO2067756052", member.iban)

        self.assertEqual(2, Subscription.objects.count())

        subscription_1 = Subscription.objects.get(member=member, product=self.product_1)
        self.assertEqual(1, subscription_1.quantity)
        self.assertEqual(self.growing_period, subscription_1.period)
        self.assertLess(self.now.date(), subscription_1.start_date)
        self.assertEqual(self.growing_period.end_date, subscription_1.end_date)

        subscription_2 = Subscription.objects.get(member=member, product=self.product_2)
        self.assertEqual(2, subscription_2.quantity)
        self.assertEqual(self.growing_period, subscription_2.period)
        self.assertLess(self.now.date(), subscription_2.start_date)
        self.assertEqual(self.growing_period.end_date, subscription_2.end_date)

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

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args[0][0]
        self.assertEqual(Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION, trigger_data.key)
        self.assertEqual(member.id, trigger_data.recipient_id_in_base_queryset)

        self.assertFalse(WaitingListEntry.objects.exists())

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
        self.assertFalse(response.json()["order_confirmed"])
        self.assertFalse(Member.objects.exists())

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
        self.assertFalse(response.json()["order_confirmed"])
        self.assertFalse(Member.objects.exists())

    @classmethod
    def build_valid_post_data_for_an_order_without_waiting_list(cls) -> dict[str, Any]:
        return {
            "shopping_cart_order": {cls.product_1.id: 1, cls.product_2.id: 2},
            "shopping_cart_waiting_list": {},
            "personal_data": cls.build_valid_personal_data(),
            "sepa_allowed": True,
            "contract_accepted": True,
            "statute_accepted": True,
            "number_of_coop_shares": 2,
            "pickup_location_ids": [cls.pickup_location.id],
            "student_status_enabled": False,
            "payment_rhythm": MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            "become_member_now": None,
        }

    @classmethod
    def build_valid_personal_data(cls):
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
            "birthdate": "1990-12-21",
            "account_owner": "John S. Doe",
            "iban": "NL37RABO2067756052",
        }
