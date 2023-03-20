from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from tapir import settings
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameters import Parameter


def send_email(to_email: [str], subject: str, content: str):
    email_body = render_to_string(
        "wirgarten/email/email_base.html",
        {"content": content, "subject": subject, "preview_text": content},
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=email_body,
        to=to_email,
        from_email=settings.EMAIL_HOST_SENDER,
        headers={
            "From": f"{get_parameter_value(Parameter.SITE_NAME)} <{settings.EMAIL_HOST_SENDER}>"
        },
    )
    email.content_subtype = "html"
    email.send()

    # TODO: create log entry
