import json
import uuid
from unittest.mock import patch, Mock

from django.urls import reverse
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.waiting_list.views import PublicConfirmWaitingListEntryView
from tapir.wirgarten.models import Member, OrderFeedback, WaitingListEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPublicConfirmWaitingListEntryView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.pickup_location = PickupLocationFactory.create()

    @patch("tapir_mail.triggers.transactional_trigger.TransactionalTrigger.fire_action")
    def test_post_waitingListEntryWithFeedback_feedbackGetsTransferredToMember(
        self, mock_fire_action: Mock
    ):
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
