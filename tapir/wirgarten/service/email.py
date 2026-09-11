from dataclasses import dataclass
from typing import List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from tapir.configuration.parameter import get_parameter_value
from tapir.log.models import EmailLogEntry
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys


@dataclass
class Attachment:
    file_name: str
    content: bytes
    mime_type: str


def send_email(
    to_email: List[str],
    subject: str,
    content: str,
    attachments: List[Attachment],
    cache: dict,
):

    email = EmailMultiAlternatives(
        subject=subject,
        body=content,
        to=to_email,
        bcc=(
            [settings.EMAIL_AUTO_BCC]
            if hasattr(settings, "EMAIL_AUTO_BCC") and settings.EMAIL_AUTO_BCC
            else None
        ),
        from_email=settings.EMAIL_HOST_SENDER,
        headers={
            "From": f"{get_parameter_value(ParameterKeys.SITE_NAME, cache=cache)} <{settings.EMAIL_HOST_SENDER}>"
        },
    )

    for attachment in attachments:
        email.attach(attachment.file_name, attachment.content, attachment.mime_type)

    email.send()

    member = Member.objects.filter(email=to_email[0]).first()
    EmailLogEntry().populate(email_message=email, user=member).save()
