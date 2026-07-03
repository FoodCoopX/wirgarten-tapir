import datetime
import json
import uuid
from decimal import Decimal
from unittest.mock import patch, Mock

from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTriggerData,
    TransactionalTrigger,
)

from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.constants import WEEKLY
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

    @patch("tapir_mail.triggers.transactional_trigger.TransactionalTrigger.fire_action")
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
        }

        response = self.client.post(
            reverse("waiting_list:public_confirm_waiting_list_entry"),
            data=json.dumps(confirm_data),
            content_type="application/json",
        )

        self.assertEqual(200, response.status_code)
        self.assert_order_confirmed(response.json())
        self.assertEqual(1, Member.objects.count())
        self.assertFalse(CoopShareTransaction.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action")
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
                "contract_list": "<ul><li>1 × M Basket  (11.05.2026 - 31.12.2026)</li></ul>",
                "membership_start_date": "07.06.2026",
                "membership_monthly_price": "0,00",
                "first_pickup_date": "14.05.2026",
                "number_of_coop_shares": 2,
                "price_of_a_coop_share": "50,00",
                "total_cost": "100,00",
                "solidarity_contribution_amount": "12,00",
                "solidarity_contribution_start_date": "11.05.2026",
            },
            trigger_data.token_data,
        )
