from django.core import mail

from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSendReport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_sendReport_withFailures_sendsMailListingFailedMembersToRecipient(self):
        recipient = MemberFactory.create()
        failed_member = MemberFactory.create()

        UnverifiedMembersService.send_report(
            recipient=recipient,
            member_count=3,
            failures=[(failed_member, "Keycloak error")],
            cache={},
        )

        self.assertEqual(1, len(mail.outbox))
        sent_mail = mail.outbox[0]
        self.assertEqual([recipient.email], sent_mail.to)
        self.assertIn("2 von 3", sent_mail.body)
        self.assertIn(f"{failed_member} : Keycloak error", sent_mail.body)

    def test_sendReport_noFailures_sendsMailWithoutFailureList(self):
        recipient = MemberFactory.create()

        UnverifiedMembersService.send_report(
            recipient=recipient, member_count=3, failures=[], cache={}
        )

        self.assertEqual(1, len(mail.outbox))
        self.assertIn("3 von 3", mail.outbox[0].body)
        self.assertNotIn("nicht gesendet", mail.outbox[0].body)
