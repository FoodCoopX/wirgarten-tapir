import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.payments.models import MemberCredit, MemberCreditSettledLogEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberCreditSettleApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_normalMemberTriesToSettle_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.post(
            reverse("payments:member_credit_settle"),
            data={"credit_ids": []},
            content_type="application/json",
        )

        self.assertStatusCode(response, 403)

    def test_post_default_setTheSettledOnFieldAndAddsLogEntry(self):
        admin_member = MemberFactory.create(is_superuser=True)
        member = MemberFactory.create()
        self.client.force_login(admin_member)

        credit = MemberCredit.objects.create(
            due_date=datetime.date(year=2025, month=1, day=1),
            member=member,
            amount=Decimal("50.00"),
            purpose="Test purpose",
            comment="Test comment",
        )

        self.assertIsNone(credit.settled_on)

        url = reverse("payments:member_credit_settle")
        response = self.client.post(
            url,
            data={"credit_ids": [credit.id]},
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        self.assertIn("1 gebucht", response.json())

        credit.refresh_from_db()
        self.assertIsNotNone(credit.settled_on)

        log_entries = MemberCreditSettledLogEntry.objects.all()
        self.assertEqual(1, log_entries.count())
        db_log_entry = log_entries.first()
        self.assertEqual(member.email, db_log_entry.user.email)
        self.assertEqual(admin_member.email, db_log_entry.actor.email)
