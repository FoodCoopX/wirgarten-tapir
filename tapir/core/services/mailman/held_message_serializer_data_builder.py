import datetime
import email
import logging
from email import policy
from email.message import EmailMessage
from email.utils import parseaddr

from django.urls import reverse
from mailmanclient.restobjects.held_message import HeldMessage

from tapir.accounts.services.email_normaliser import EmailNormaliser
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today

LOG = logging.getLogger(__name__)


class HeldMessageSerializerDataBuilder:
    @classmethod
    def build_serializer_data(
        cls,
        held_message: HeldMessage,
        members_by_email: dict[str, Member],
        cache: dict,
    ):
        message = email.message_from_string(held_message.msg, policy=policy.default)
        member = members_by_email.get(EmailNormaliser.normalise(held_message.sender))

        return {
            "request_id": held_message.request_id,
            "sender": held_message.sender,
            "sender_name": (
                member.get_display_name()
                if member is not None
                else cls.extract_sender_display_name(message)
            ),
            "formatted_member_number": (
                cls.get_formatted_member_number(member, cache=cache)
                if member is not None
                else None
            ),
            "link_to_member_profile": (
                reverse("wirgarten:member_detail", kwargs={"pk": member.id})
                if member is not None
                else None
            ),
            "subject": held_message.subject or "",
            "reason": held_message.reason or "",
            "hold_date": datetime.datetime.fromisoformat(
                held_message.hold_date
            ).replace(tzinfo=datetime.timezone.utc),
            "body": cls.extract_body(message),
        }

    @classmethod
    def get_formatted_member_number(cls, member: Member, cache: dict) -> str | None:
        if not MemberNumberService.should_display_member_number(
            member=member, reference_date=get_today(cache=cache), cache=cache
        ):
            return None
        return MemberNumberService.format_member_number(member.member_no, cache=cache)

    @classmethod
    def extract_sender_display_name(cls, message: EmailMessage) -> str | None:
        display_name, _ = parseaddr(message.get("From", ""))
        return display_name or None

    @classmethod
    def extract_body(cls, message: EmailMessage) -> str:
        body = message.get_body(preferencelist=("plain", "html"))
        if body is None:
            return ""
        try:
            return body.get_content()
        except Exception:
            LOG.exception("Failed to read the body of a held message")
            return "(Der Inhalt der E-Mail konnte nicht gelesen werden.)"
