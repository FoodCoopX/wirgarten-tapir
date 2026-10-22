import datetime
import email
from email import policy

from mailmanclient.restobjects.held_message import HeldMessage


class HeldMessageSerializerDataBuilder:
    @classmethod
    def build_serializer_data(cls, held_message: HeldMessage):
        return {
            "request_id": held_message.request_id,
            "sender": held_message.sender,
            "subject": held_message.subject or "",
            "reason": held_message.reason or "",
            "hold_date": datetime.datetime.fromisoformat(
                held_message.hold_date
            ).replace(tzinfo=datetime.timezone.utc),
            "body": cls.extract_body(held_message.msg),
        }

    @classmethod
    def extract_body(cls, raw_message: str) -> str:
        message = email.message_from_string(raw_message, policy=policy.default)
        body = message.get_body(preferencelist=("plain", "html"))
        if body is None:
            return ""
        return body.get_content()
