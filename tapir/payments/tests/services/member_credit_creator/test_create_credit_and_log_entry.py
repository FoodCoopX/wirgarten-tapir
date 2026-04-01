import datetime
from decimal import Decimal

from tapir.payments.models import MemberCredit, MemberCreditCreatedLogEntry
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreateCreditAndLogEntry(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_createCreditAndLogEntry_default_createsBothObjects(self):
        member = MemberFactory.create()
        actor = MemberFactory.create()
        comment = "test comment"

        MemberCreditCreator.create_credit_and_log_entry(
            member=member,
            amount_to_credit=12.7,
            comment=comment,
            actor=actor,
            reference_date=datetime.date(year=2027, month=6, day=19),
        )

        member_credit = MemberCredit.objects.get()
        self.assertEqual(Decimal("12.70"), member_credit.amount)
        self.assertEqual(comment, member_credit.comment)
        self.assertEqual(member.id, member_credit.member_id)
        self.assertEqual(
            datetime.date(year=2027, month=6, day=30), member_credit.due_date
        )

        log_entry = MemberCreditCreatedLogEntry.objects.get()
        self.assertTrue(
            {"member", "amount", "comment", "due_date"}.issubset(
                set(log_entry.values.keys())
            )
        )
