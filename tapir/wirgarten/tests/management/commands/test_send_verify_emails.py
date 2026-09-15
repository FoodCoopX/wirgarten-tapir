from unittest.mock import patch

from django.core.management import call_command

from tapir.wirgarten.management.commands.send_verify_emails import Command
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import CoopShareTransactionFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSendVerifyEmailsCommand(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(Command, "send_emails", autospec=True)
    def test_handle_membersWithCompoundLastNameAndNoMemberNumber_sortedCaseInsensitivelyByLastName(
        self, mock_send_emails
    ):
        self._set_parameter(ParameterKeys.MEMBER_BYPASS_KEYCLOAK, True)
        vogel = MemberFactory.create(last_name="Vogel")
        von_adler = MemberFactory.create(last_name="von Adler")
        voss = MemberFactory.create(last_name="Voss")
        for member in [vogel, von_adler, voss]:
            CoopShareTransactionFactory.create(member=member)
        # member_no is the primary ordering field, so it must be null here for
        # all three members, otherwise it alone determines the order and the
        # last_name tiebreaker this test is meant to exercise never applies.
        Member.objects.filter(id__in=[vogel.id, von_adler.id, voss.id]).update(
            member_no=None
        )

        call_command("send_verify_emails")

        mock_send_emails.assert_called_once()
        sorted_member_ids = {vogel.id, von_adler.id, voss.id}
        last_names = [
            member.last_name
            for member in mock_send_emails.call_args.args[1]
            if member.id in sorted_member_ids
        ]
        self.assertEqual(["Vogel", "von Adler", "Voss"], last_names)
