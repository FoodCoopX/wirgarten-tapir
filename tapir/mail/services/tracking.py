from django.conf import settings
from django.utils import timezone
from django.urls import reverse

from tapir.mail.models import EmailDispatch


def track_email_opening(email_dispatch: EmailDispatch):
    if email_dispatch.opened_time:
        # email was already opened before
        return

    email_dispatch.opened_time = timezone.now()
    email_dispatch.save()


def get_tracking_url(email_dispatch: EmailDispatch):
    return f"{settings.SITE_URL}{reverse('tracking-track', args=[email_dispatch.id])}"


def add_tracking_pixel(html_content: str, pixel_url: str):
    return html_content.replace(
        "</body>", f'<img src="{pixel_url}" style="display:none"/></body>', 1
    )
