from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from tapir.mail.config import BccProvider
from tapir.mail.service.mjml import mjml2html
from tapir.mail.service.tracking import add_tracking_pixel


def prepare_email(
    mjml: str | None = None,
    subject: str | None = None,
    recipients=None,
    tracking_url: str | None = None,
    tracking_id: str | None = None,
    bcc_provider: BccProvider | None = None,
):
    """
    Sends an email using the configuration provided in the kwargs.
    """

    if not mjml:
        raise ValueError("mjml is required")

    return build_email(
        html=mjml2html(mjml),
        subject=subject,
        recipients=recipients,
        tracking_url=tracking_url,
        tracking_id=tracking_id,
        bcc_provider=bcc_provider,
    )


def build_email(
    html: str,
    subject: str | None = None,
    recipients=None,
    tracking_url: str | None = None,
    tracking_id: str | None = None,
    bcc_provider: BccProvider | None = None,
):
    if recipients is None:
        recipients = []

    if not recipients:
        raise ValueError("recipients is required")

    email_body = html

    if tracking_url:
        email_body = add_tracking_pixel(email_body, tracking_url)

    reply_to = None
    if getattr(settings, "EMAIL_REPLY_TO", None) is not None:
        reply_to = [settings.EMAIL_REPLY_TO]

    bcc_addresses = []
    if getattr(settings, "EMAIL_AUTO_BCC", None) is not None:
        bcc_addresses.append(settings.EMAIL_AUTO_BCC)

    if bcc_provider is not None:
        bcc_address = bcc_provider()
        if bcc_address:
            bcc_addresses.append(bcc_address)

    email = EmailMultiAlternatives(
        subject=subject,
        body=email_body,
        to=recipients if isinstance(recipients, list) else [recipients],
        bcc=bcc_addresses,
        from_email=_build_from_email(settings.EMAIL_BOUNCE_ADDRESS, tracking_id),
        headers={
            "From": f"{settings.EMAIL_HOST_SENDER_NAME} <{settings.EMAIL_HOST_SENDER}>",
        },
        reply_to=reply_to,
    )
    email.content_subtype = "html"

    return email


def _build_from_email(email_host_sender: str, tracking_id: str):
    prefix, suffix = email_host_sender.split("@")
    return f"{prefix}+{tracking_id}@{suffix}"


def _get_dispatch_id_from_email_return_path(email_from: str | None):
    if not email_from or "@" not in email_from:
        return None

    prefix, _ = email_from.split("@", maxsplit=1)
    if "+" not in prefix:
        return None

    return prefix.split("+")[-1]
