import email
import logging
from email.message import Message
from email.utils import parseaddr
from imaplib import IMAP4_SSL, IMAP4

from django.conf import settings
from django.utils import timezone
from flufl.bounce import all_failures

from tapir.mail.models import EmailDispatch
from tapir.mail.services.email import _get_dispatch_id_from_email_return_path

LOG = logging.getLogger(__name__)


class EmailBounceException(Exception):
    pass


class EmailBounces:
    @classmethod
    def check_for_bounces(cls):
        if not settings.EMAIL_BOUNCE_USER or not settings.EMAIL_BOUNCE_PASSWORD:
            LOG.debug("Missing bounce user or bounce password, cancelling bounce check")
            return

        mail_client = IMAP4_SSL(
            settings.EMAIL_BOUNCE_HOST, port=settings.EMAIL_PORT_IMAP
        )
        return_code, _ = mail_client.login(
            settings.EMAIL_BOUNCE_USER, settings.EMAIL_BOUNCE_PASSWORD
        )
        if return_code != "OK":
            raise EmailBounceException(
                f"Imap server login failed, return code : {return_code}"
            )

        try:
            mail_client.select(readonly=settings.DEBUG)

            domain = settings.EMAIL_BOUNCE_ADDRESS.split("@")[1]
            search_criteria = f'(UNSEEN HEADER X-Original-To "@{domain}")'
            return_code, messages_id_blocks = mail_client.search(None, search_criteria)
            if return_code != "OK":
                raise EmailBounceException(
                    f"Imap server search failed, return code : {return_code}"
                )
            if not messages_id_blocks:
                LOG.info("Nothing to check for in EmailBounces.check_for_bounces")
                return

            for block in messages_id_blocks:
                for message_id in block.split():
                    cls.process_message(mail_client, message_id.decode())
        finally:
            mail_client.logout()

    @classmethod
    def process_message(cls, mail_client: IMAP4, message_id: str):
        return_code, message_bytes = mail_client.fetch(message_id, "(BODY.PEEK[])")
        if return_code != "OK":
            raise EmailBounceException(
                f"Failed to get message with id : {message_id}, return code : {return_code}"
            )

        message = email.message_from_bytes(message_bytes[0][1])

        if not cls.belongs_to_this_instance(message):
            LOG.debug("Message belongs to another instance, leaving it untouched")
            return

        dispatch_id = cls.get_return_path_from_headers(
            message,
            [
                "Return-Path",
                "X-Original-To",
                "Delivered-To",
                "To",
            ],
        )
        if not dispatch_id:
            dispatch_id = cls._get_envid_from_dsn_from_message(message)

        if not dispatch_id:
            LOG.debug(f"Email is not a bounce : {message.as_string()}")
            cls.mark_as_seen(mail_client, message_id)
            return

        email_dispatch: EmailDispatch = EmailDispatch.objects.filter(
            id=dispatch_id
        ).first()

        if not email_dispatch:
            LOG.debug(f"Can't find email dispatch with dispatch id {dispatch_id}")
            cls.mark_as_seen(mail_client, message_id)
            return

        message_uid = message.get("Message-Id", None)
        if not message_uid:
            LOG.debug("Missing Message-Id, can't process")
            cls.mark_as_seen(mail_client, message_id)
            return

        cls.save_and_log_dsn_message(
            message=message,
            email_dispatch=email_dispatch,
            dispatch_id=dispatch_id,
            message_uid=message_uid,
        )

        cls.mark_as_seen(mail_client, message_id)

    @classmethod
    def belongs_to_this_instance(cls, message: Message) -> bool:
        expected_local, expected_domain = settings.EMAIL_BOUNCE_ADDRESS.split("@")
        for header in ("X-Original-To", "To"):
            value = message.get(header)
            if not value or "@" not in value:
                continue
            address = parseaddr(value)[1]
            local_part, domain = address.split("@")
            # strip the VERP extension: "bounce+<dispatch_id>" -> "bounce"
            local_part = local_part.split("+")[0]
            if local_part == expected_local and domain == expected_domain:
                return True
        return False

    @classmethod
    def mark_as_seen(cls, mail_client: IMAP4, message_id: str):
        mail_client.store(message_id, "+FLAGS", "(\\Seen)")

    @classmethod
    def save_and_log_dsn_message(
        cls,
        message: Message,
        email_dispatch: EmailDispatch,
        dispatch_id: str,
        message_uid: str,
    ):
        dsn_action = cls._get_dsn_action_from_message(message)

        if dsn_action in ("delivered", "relayed", "expanded"):
            email_dispatch.dsn_delivered_time = timezone.now()
            email_dispatch.save()
        elif dsn_action == "delayed":
            LOG.info(
                f"DSN delay notification for dispatch {dispatch_id}, message id: {message_uid}"
            )
        else:
            email_dispatch.bounce_message = f"Email could not be delivered, bounce message id : {message_uid}, dsn_action: {dsn_action}"
            email_dispatch.bounce_type = cls.determine_bounce_type(
                message, email_dispatch.recipient
            )
            email_dispatch.save()

    @classmethod
    def _get_dsn_action_from_message(cls, message: Message):
        content_type = message.get_content_type()
        if content_type != "multipart/report":
            return None

        for part in message.walk():
            action = cls._get_dsn_action_from_message_part(part)
            if action:
                return action

        return None

    @staticmethod
    def _get_dsn_action_from_message_part(part: Message):
        if part.get_content_type() != "message/delivery-status":
            return None
        payload = part.get_payload()
        if isinstance(payload, list):
            for dsn_part in payload:
                action = dsn_part.get("Action", None)
                if action:
                    return action.strip().lower()
        elif isinstance(payload, str):
            for line in payload.splitlines():
                if line.lower().startswith("action:"):
                    return line.split(":", 1)[1].strip().lower()
        return None

    @classmethod
    def _get_envid_from_dsn_from_message(cls, message: Message):
        content_type = message.get_content_type()
        if content_type != "multipart/report":
            return None

        for part in message.walk():
            envid = cls._get_envid_from_dsn_from_message_part(part)
            if envid:
                return envid

        return None

    @classmethod
    def _get_envid_from_dsn_from_message_part(cls, part: Message):
        if part.get_content_type() != "message/delivery-status":
            return None

        payload = part.get_payload()
        if isinstance(payload, list):
            for dsn_part in payload:
                envid = dsn_part.get("Original-Envelope-Id", None)
                if envid:
                    return envid.strip()
        elif isinstance(payload, str):
            for line in payload.splitlines():
                if line.lower().startswith("original-envelope-id:"):
                    return line.split(":", 1)[1].strip()
        return None

    @staticmethod
    def get_return_path_from_headers(message: Message, headers: list[str]):
        for header in headers:
            dispatch_id = _get_dispatch_id_from_email_return_path(
                message.get(header, None)
            )
            if dispatch_id:
                return dispatch_id

        return None

    @staticmethod
    def determine_bounce_type(message: Message, recipient_address: str):
        # flufl.bounce returns the addresses as bytes.
        soft, hard = all_failures(message)
        recipient_address = recipient_address.encode()
        if recipient_address in hard:
            return EmailDispatch.BounceTypes.HARD
        if recipient_address in soft:
            return EmailDispatch.BounceTypes.SOFT
        return EmailDispatch.BounceTypes.UNKNOWN
