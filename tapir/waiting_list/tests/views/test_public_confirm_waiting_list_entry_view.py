import datetime
import json
import uuid
from unittest.mock import patch, Mock

from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import TransactionalTriggerData

from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    OrderFeedback,
    WaitingListEntry,
    WaitingListProductWish,
    Subscription,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    GrowingPeriodFactory,
    ProductFactory,
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
