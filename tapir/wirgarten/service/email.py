from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

from tapir import settings


def send_email(to_email: [str], subject: str, content: str):
    email_body = render_to_string(
        "wirgarten/email/email_base.html", {"content": content, "subject": subject}
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=email_body,
        to=to_email,
        from_email=settings.EMAIL_HOST_SENDER,
    )
    email.content_subtype = "html"
    email.send()

    # TODO: create log entry
