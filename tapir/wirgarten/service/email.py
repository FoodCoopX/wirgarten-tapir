from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from tapir import settings
from tapir.configuration.parameter import get_parameter_value
from tapir.log.models import EmailLogEntry
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import generate_future_deliveries
from tapir.wirgarten.utils import format_date


def send_email(to_email: [str], subject: str, content: str, variables: dict = {}):
    variables.update(get_default_vars(to_email))
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
        bcc=[settings.EMAIL_AUTO_BCC] if hasattr(settings, "EMAIL_AUTO_BCC") else None,
        from_email=settings.EMAIL_HOST_SENDER,
        headers={
            "From": f"{get_parameter_value(Parameter.SITE_NAME)} <{settings.EMAIL_HOST_SENDER}>"
        },
    )
    email.content_subtype = "html"
    email.send()

    found_member = Member.objects.filter(email=to_email[0])
    EmailLogEntry().populate(
        email_message=email, user=found_member[0] if found_member.exists() else None
    ).save()


def get_default_vars(to_email):
    variables = add_member_vars(to_email)
    variables.update(add_general_vars())
    return variables


def add_general_vars():
    today = date.today()
    return {
        "year_current": today.year,
        "year_next": (today + relativedelta(years=1)).year,
        "year_overnext": (today + relativedelta(years=2)).year,
        "admin_name": get_parameter_value(Parameter.SITE_ADMIN_NAME),
        "site_name": get_parameter_value(Parameter.SITE_NAME),
        "admin_telephone": get_parameter_value(Parameter.SITE_ADMIN_TELEPHONE),
        "admin_image": get_parameter_value(Parameter.SITE_ADMIN_IMAGE),
        "site_email": get_parameter_value(Parameter.SITE_EMAIL),
    }


def add_member_vars(to_email):
    try:
        from tapir.wirgarten.models import Member

        member = Member.objects.get(email=to_email[0])
        future_deliveries = generate_future_deliveries(member)
        return {
            "member": member,
            # FIXME: return None is not optimal...
            "last_pickup_date": format_date(
                datetime.strptime(
                    future_deliveries[-1]["delivery_date"], "%Y-%m-%d"
                ).date()
            )
            if len(future_deliveries) > 0
            else None,
        }
    except Member.DoesNotExist:
        return {}
