from tapir.wirgarten.models import Member, OrderFeedback, WaitingListEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.views.admin_dashboard import get_recent_feedbacks


class TestGetRecentFeedbacks(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_get_recent_feedbacks_includesMemberFeedback(self):
        member = MemberFactory.create()
        OrderFeedback.objects.create(
            member=member, feedback_text="Member feedback text"
        )

        feedbacks = get_recent_feedbacks(limit=10)

        self.assertEqual(1, len(feedbacks))
        self.assertEqual("Member feedback text", feedbacks[0]["feedback_text"])
        self.assertEqual(member.pk, feedbacks[0]["member__pk"])
        self.assertEqual(member.first_name, feedbacks[0]["member__first_name"])
        self.assertIsNone(feedbacks[0]["waiting_list_entry__pk"])

    def test_get_recent_feedbacks_includesWaitingListEntryFeedback(self):
        entry = WaitingListEntryFactory.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        OrderFeedback.objects.create(
            waiting_list_entry=entry, feedback_text="Waiting list feedback text"
        )

        feedbacks = get_recent_feedbacks(limit=10)

        self.assertEqual(1, len(feedbacks))
        self.assertEqual("Waiting list feedback text", feedbacks[0]["feedback_text"])
        self.assertIsNone(feedbacks[0]["member__pk"])
        self.assertEqual(entry.pk, feedbacks[0]["waiting_list_entry__pk"])
        self.assertEqual("John", feedbacks[0]["waiting_list_entry__first_name"])
        self.assertEqual("Doe", feedbacks[0]["waiting_list_entry__last_name"])
        self.assertEqual("john@example.com", feedbacks[0]["waiting_list_entry__email"])

    def test_get_recent_feedbacks_respectsLimit(self):
        member = MemberFactory.create()
        for i in range(5):
            OrderFeedback.objects.create(member=member, feedback_text=f"Feedback {i}")

        feedbacks = get_recent_feedbacks(limit=3)

        self.assertEqual(3, len(feedbacks))
