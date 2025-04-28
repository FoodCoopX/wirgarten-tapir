from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from tapir.configuration.parameter import get_parameter_value
from tapir.log.models import EmailLogEntry
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import generate_future_deliveries
from tapir.wirgarten.utils import format_date, get_today


@dataclass
class Attachment:
    file_name: str
    content: str
    mime_type: str


def send_email(
    to_email: List[str],
    subject: str,
    content: str,
    variables: dict = None,
    attachments: List[Attachment] = None,
    cache: Dict = None,
):
    """
    Send an email to a list of recipients. The email is sent as HTML using the email/email_base.html template.

    :param to_email: list of email addresses
    :param subject: subject of the email
    :param content: content of the email
    :param variables: additional variables to be used in the email template
    :param attachments: attached files
    """

    if variables is None:
        variables = {}
    if attachments is None:
        attachments = []

    variables.update(get_default_vars(to_email, cache=cache))
    content = content.format(**variables)

    email_body = render_to_string(
        "wirgarten/email/email_base.html",
        {
            "content": content,
            "subject": subject,
            "preview_text": content,
            "member_area_link": settings.SITE_URL,
        },
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=email_body,
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

    email.content_subtype = "html"
    email.send()

    found_member = Member.objects.filter(email=to_email[0])
    EmailLogEntry().populate(
        email_message=email, user=found_member[0] if found_member.exists() else None
    ).save()


# all the vars stuff will be deprecated as soon as the mail module is going in production
def get_default_vars(to_email, cache: Dict):
    variables = add_member_vars(to_email, cache=cache)
    variables.update(add_general_vars(cache=cache))
    return variables


def add_general_vars(cache: Dict):
    today = get_today(cache=cache)
    return {
        "year_current": today.year,
        "year_next": (today + relativedelta(years=1)).year,
        "year_overnext": (today + relativedelta(years=2)).year,
        "admin_name": get_parameter_value(ParameterKeys.SITE_ADMIN_NAME, cache=cache),
        "site_name": get_parameter_value(ParameterKeys.SITE_NAME, cache=cache),
        "admin_telephone": get_parameter_value(
            ParameterKeys.SITE_ADMIN_TELEPHONE, cache=cache
        ),
        "admin_image": get_parameter_value(ParameterKeys.SITE_ADMIN_IMAGE, cache=cache),
        "site_email": get_parameter_value(ParameterKeys.SITE_EMAIL, cache=cache),
    }


def add_member_vars(to_email, cache: Dict):
    try:
        from tapir.wirgarten.models import Member

        member = Member.objects.get(email=to_email[0])
        future_deliveries = generate_future_deliveries(member, cache=cache)
        return {
            "member": member,
            # FIXME: return None is not optimal...
            "last_pickup_date": (
                format_date(
                    datetime.strptime(
                        future_deliveries[-1]["delivery_date"], "%Y-%m-%d"
                    ).date()
                )
                if len(future_deliveries) > 0
                else None
            ),
        }
    except Member.DoesNotExist:
        return {}
