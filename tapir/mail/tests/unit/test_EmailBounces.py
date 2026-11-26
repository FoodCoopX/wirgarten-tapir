from email.message import Message
from unittest.mock import patch, Mock, call

from django.conf import settings
from django.test import override_settings

from tapir.mail.models import EmailDispatch
from tapir.mail.service.email_bounces import EmailBounces
from tapir.wirgarten.tests.test_utils import TapirUnitTest

BOUNCE_DOMAIN = "mail.net"
BOUNCE_ADDRESS = f"bounce@{BOUNCE_DOMAIN}"
BOUNCE_USER = "Test bounce user"
BOUNCE_PASSWORD = "Email bounce password"


@override_settings(
    EMAIL_BOUNCE_HOST="bounce.example.org",
    EMAIL_BOUNCE_ADDRESS=BOUNCE_ADDRESS,
    EMAIL_BOUNCE_USER=BOUNCE_USER,
    EMAIL_BOUNCE_PASSWORD=BOUNCE_PASSWORD,
)
class TestEmailBounces(TapirUnitTest):
    @patch("tapir.mail.service.email_bounces.IMAP4_SSL")
    def test_checkForBounces_loginFails_raisesException(
        self, mock_mail_client_constructor: Mock
    ):
        mock_mail_client = Mock()
        mock_mail_client_constructor.return_value = mock_mail_client
        mock_mail_client.login.return_value = ("ERROR", [])

        with self.assertRaises(Exception):
            EmailBounces.check_for_bounces()

        mock_mail_client_constructor.assert_called_once_with(
            settings.EMAIL_BOUNCE_HOST, port=settings.EMAIL_PORT_IMAP
        )
        mock_mail_client.login.assert_called_once_with(
            settings.EMAIL_BOUNCE_USER, settings.EMAIL_BOUNCE_PASSWORD
        )
        mock_mail_client.search.assert_not_called()

    @override_settings(EMAIL_BOUNCE_USER=None, EMAIL_BOUNCE_PASSWORD=None)
    @patch("tapir.mail.service.email_bounces.IMAP4_SSL")
    def test_checkForBounces_missingCredentials_doesNothing(
        self, mock_mail_client_constructor: Mock
    ):
        EmailBounces.check_for_bounces()

        mock_mail_client_constructor.assert_not_called()

    @patch("tapir.mail.service.email_bounces.IMAP4_SSL")
    def test_checkForBounces_searchFails_raisesExceptionAndLogsOut(
        self, mock_mail_client_constructor: Mock
    ):
        mock_mail_client = Mock()
        mock_mail_client_constructor.return_value = mock_mail_client
        mock_mail_client.login.return_value = ("OK", None)
        mock_mail_client.search.return_value = ("ERROR", [])

        with self.assertRaises(Exception):
            EmailBounces.check_for_bounces()

        mock_mail_client_constructor.assert_called_once_with(
            settings.EMAIL_BOUNCE_HOST, port=settings.EMAIL_PORT_IMAP
        )
        mock_mail_client.login.assert_called_once_with(
            settings.EMAIL_BOUNCE_USER, settings.EMAIL_BOUNCE_PASSWORD
        )
        mock_mail_client.select.assert_called_once()
        mock_mail_client.search.assert_called_once_with(
            None, f'(UNSEEN HEADER X-Original-To "@{BOUNCE_DOMAIN}")'
        )
        mock_mail_client.logout.assert_called_once_with()

    @patch("tapir.mail.service.email_bounces.IMAP4_SSL")
    @patch("tapir.mail.service.email_bounces.EmailBounces.process_message")
    def test_checkForBounces_default_processesAllMessagesReturnedByImapSearch(
        self, mock_process_message: Mock, mock_mail_client_constructor: Mock
    ):
        mock_mail_client = Mock()
        mock_mail_client_constructor.return_value = mock_mail_client
        mock_mail_client.login.return_value = ("OK", None)
        mock_mail_client.search.return_value = ("OK", [b"a b c", b"d e f"])

        EmailBounces.check_for_bounces()

        mock_mail_client_constructor.assert_called_once_with(
            settings.EMAIL_BOUNCE_HOST, port=settings.EMAIL_PORT_IMAP
        )
        mock_mail_client.login.assert_called_once_with(
            settings.EMAIL_BOUNCE_USER, settings.EMAIL_BOUNCE_PASSWORD
        )
        mock_mail_client.select.assert_called_once()
        mock_mail_client.search.assert_called_once_with(
            None, f'(UNSEEN HEADER X-Original-To "@{BOUNCE_DOMAIN}")'
        )
        self.assertEqual(6, mock_process_message.call_count)
        mock_process_message.assert_has_calls(
            [
                call(mock_mail_client, message_id)
                for message_id in ["a", "b", "c", "d", "e", "f"]
            ]
        )
        mock_mail_client.logout.assert_called_once_with()

    @patch("tapir.mail.service.email_bounces.all_failures")
    def test_determineBounceType_recipientAddressIsInBothSoftAndHard_returnsHard(
        self, mock_all_failures: Mock
    ):
        message = Message()
        recipient_address = "test@test.de"
        mock_all_failures.return_value = ([recipient_address], [recipient_address])

        result = EmailBounces.determine_bounce_type(message, recipient_address)

        mock_all_failures.assert_called_once_with(message)
        self.assertEqual(EmailDispatch.BounceTypes.HARD, result)

    @patch("tapir.mail.service.email_bounces.all_failures")
    def test_determineBounceType_recipientAddressIsOnlyInHard_returnsHard(
        self, mock_all_failures: Mock
    ):
        message = Message()
        recipient_address = "test@test.de"
        mock_all_failures.return_value = (["other@test.de"], [recipient_address])

        result = EmailBounces.determine_bounce_type(message, recipient_address)

        mock_all_failures.assert_called_once_with(message)
        self.assertEqual(EmailDispatch.BounceTypes.HARD, result)

    @patch("tapir.mail.service.email_bounces.all_failures")
    def test_determineBounceType_recipientAddressIsOnlyInSoft_returnsHard(
        self, mock_all_failures: Mock
    ):
        message = Message()
        recipient_address = "test@test.de"
        mock_all_failures.return_value = ([recipient_address], ["other@test.de"])

        result = EmailBounces.determine_bounce_type(message, recipient_address)

        mock_all_failures.assert_called_once_with(message)
        self.assertEqual(EmailDispatch.BounceTypes.SOFT, result)

    @patch("tapir.mail.service.email_bounces.all_failures")
    def test_determineBounceType_recipientAddressIsNotReturned_returnsUnknown(
        self, mock_all_failures: Mock
    ):
        message = Message()
        recipient_address = "test@test.de"
        mock_all_failures.return_value = (["other@test.de"], ["other@test.de"])

        result = EmailBounces.determine_bounce_type(message, recipient_address)

        mock_all_failures.assert_called_once_with(message)
        self.assertEqual(EmailDispatch.BounceTypes.UNKNOWN, result)

    def test_processMessage_fetchFails_raisesException(self):
        mail_client = Mock()
        mail_client.fetch.side_effect = Exception()
        message_id = "message_id"

        with self.assertRaises(Exception):
            EmailBounces.process_message(mail_client, message_id)

        mail_client.fetch.assert_called_once_with(message_id, "(BODY.PEEK[])")

    @patch("tapir.mail.service.email_bounces.email.message_from_bytes")
    def test_processMessage_noDispatchId_doesNothing(
        self, mock_message_from_bytes: Mock
    ):
        mail_client = Mock()
        message_content = Mock()
        message_bytes = [[None, message_content]]
        mail_client.fetch.return_value = ("OK", message_bytes)
        message_id = "message_id"
        message = Message()
        message["Return-Path"] = "no_dispatch_id@test.de"
        message["X-Original-To"] = settings.EMAIL_BOUNCE_ADDRESS
        mock_message_from_bytes.return_value = message

        EmailBounces.process_message(mail_client, message_id)

        mail_client.fetch.assert_called_once_with(message_id, "(BODY.PEEK[])")
        mock_message_from_bytes.assert_called_once_with(message_content)

    @patch("tapir.mail.service.email_bounces.LOG")
    @patch.object(EmailDispatch.objects, "filter")
    @patch("tapir.mail.service.email_bounces.email.message_from_bytes")
    def test_processMessage_noDispatchForId_logsWarning(
        self, mock_message_from_bytes: Mock, mock_filter: Mock, mock_log: Mock
    ):
        mail_client = Mock()
        message_content = Mock()
        message_bytes = [[None, message_content]]
        mail_client.fetch.return_value = ("OK", message_bytes)
        message_id = "message_id"
        message = Message()
        message["Return-Path"] = "test+dispatch_id@test.de"
        message["X-Original-To"] = settings.EMAIL_BOUNCE_ADDRESS
        mock_message_from_bytes.return_value = message
        mock_filter.return_value = Mock()
        mock_filter.return_value.first.return_value = None

        EmailBounces.process_message(mail_client, message_id)

        mail_client.fetch.assert_called_once_with(message_id, "(BODY.PEEK[])")
        mock_message_from_bytes.assert_called_once_with(message_content)
        mock_filter.assert_called_once_with(id="dispatch_id")
        mock_log.debug.assert_called_once()
        mock_filter.return_value.first.assert_called_once_with()

    @patch("tapir.mail.service.email_bounces.EmailBounces.determine_bounce_type")
    @patch.object(EmailDispatch.objects, "filter")
    @patch("tapir.mail.service.email_bounces.email.message_from_bytes")
    def test_processMessage_dispatchFound_dispatchGetsUpdated(
        self,
        mock_message_from_bytes: Mock,
        mock_filter: Mock,
        mock_determine_bounce_type: Mock,
    ):
        mail_client = Mock()
        message_content = Mock()
        message_bytes = [[None, message_content]]
        mail_client.fetch.return_value = ("OK", message_bytes)
        message_id = "message_id"
        message_uid = "message_uid"
        message = Message()
        message["Message-Id"] = message_uid
        message["Return-Path"] = "test+dispatch_id@test.de"
        message["X-Original-To"] = settings.EMAIL_BOUNCE_ADDRESS
        mock_message_from_bytes.return_value = message
        mock_filter.return_value = Mock()
        mock_dispatch = Mock()
        mock_dispatch.recipient = "recipient.@test.de"
        mock_filter.return_value.first.return_value = mock_dispatch
        mock_determine_bounce_type.return_value = "test_bounce_type"

        EmailBounces.process_message(mail_client, message_id)

        self.assertEqual(
            f"Email could not be delivered, bounce message id : {message_uid}, dsn_action: None",
            mock_dispatch.bounce_message,
        )
        self.assertEqual(
            "test_bounce_type",
            mock_dispatch.bounce_type,
        )
        mock_dispatch.save.assert_called_once_with()

        mail_client.fetch.assert_called_once_with(message_id, "(BODY.PEEK[])")
        mock_message_from_bytes.assert_called_once_with(message_content)
        mail_client.store.assert_called_once_with(message_id, "+FLAGS", "(\\Seen)")
        mock_filter.assert_called_once_with(id="dispatch_id")
        mock_filter.return_value.first.assert_called_once_with()
        mock_determine_bounce_type.assert_called_once_with(
            message, "recipient.@test.de"
        )

    @patch("tapir.mail.service.email_bounces.EmailBounces.determine_bounce_type")
    @patch.object(EmailDispatch.objects, "filter")
    @patch("tapir.mail.service.email_bounces.email.message_from_bytes")
    def test_processMessage_messageHasNoReturnPath_otherHeaderGetsUsed(
        self,
        mock_message_from_bytes: Mock,
        mock_filter: Mock,
        mock_determine_bounce_type: Mock,
    ):
        mail_client = Mock()
        message_content = Mock()
        message_bytes = [[None, message_content]]
        mail_client.fetch.return_value = ("OK", message_bytes)
        message_id = "message_id"
        message_uid = "message_uid"
        message = Message()
        message["Message-Id"] = message_uid
        message["Return-Path"] = "<>"
        message["To"] = f"bounce+dispatch_id@{BOUNCE_DOMAIN}"
        mock_message_from_bytes.return_value = message
        mock_filter.return_value = Mock()
        mock_dispatch = Mock()
        mock_dispatch.recipient = "recipient.@test.de"
        mock_filter.return_value.first.return_value = mock_dispatch
        mock_determine_bounce_type.return_value = "test_bounce_type"

        EmailBounces.process_message(mail_client, message_id)

        mock_filter.assert_called_once_with(id="dispatch_id")

    def test_belongsToThisInstance_addressOfAnotherInstance_returnsFalse(self):
        message = Message()
        message["X-Original-To"] = "bounce+dispatch_id@other-instance.net"

        self.assertFalse(EmailBounces.belongs_to_this_instance(message))

    def test_belongsToThisInstance_ownAddressWithVerpExtension_returnsTrue(self):
        message = Message()
        message["X-Original-To"] = f"bounce+dispatch_id@{BOUNCE_DOMAIN}"

        self.assertTrue(EmailBounces.belongs_to_this_instance(message))

    def test_belongsToThisInstance_ownAddressWithoutVerpExtension_returnsTrue(self):
        # Keycloak sends with the plain bounce address, without a dispatch id
        message = Message()
        message["X-Original-To"] = BOUNCE_ADDRESS

        self.assertTrue(EmailBounces.belongs_to_this_instance(message))

    def test_belongsToThisInstance_sameDomainButOtherLocalPart_returnsFalse(self):
        message = Message()
        message["X-Original-To"] = f"other-bounce+dispatch_id@{BOUNCE_DOMAIN}"

        self.assertFalse(EmailBounces.belongs_to_this_instance(message))

    @patch.object(EmailDispatch.objects, "filter")
    @patch("tapir.mail.service.email_bounces.email.message_from_bytes")
    def test_processMessage_messageOfAnotherInstance_leavesItUnread(
        self, mock_message_from_bytes: Mock, mock_filter: Mock
    ):
        mail_client = Mock()
        message_content = Mock()
        mail_client.fetch.return_value = ("OK", [[None, message_content]])
        message_id = "message_id"
        message = Message()
        message["Message-Id"] = "message_uid"
        message["Return-Path"] = "bounce+dispatch_id@other-instance.net"
        message["X-Original-To"] = "bounce+dispatch_id@other-instance.net"
        mock_message_from_bytes.return_value = message

        EmailBounces.process_message(mail_client, message_id)

        mail_client.fetch.assert_called_once_with(message_id, "(BODY.PEEK[])")
        mail_client.store.assert_not_called()
        mock_filter.assert_not_called()
