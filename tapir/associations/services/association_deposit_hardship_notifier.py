from django.conf import settings
from django.db import transaction
from django.urls import reverse

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.email import send_email


class AssociationDepositHardshipNotifier:
    @staticmethod
    def notify_administration(member: Member, cache: dict):
        recipient = get_parameter_value(
            ParameterKeys.SITE_ADMIN_EMAIL, cache=cache
        ).strip()
        if not recipient:
            return
        name = get_parameter_value(ParameterKeys.ASSOCIATION_DEPOSIT_NAME, cache=cache)
        url = settings.SITE_URL.rstrip("/") + reverse(
            "associations:deposit_case", kwargs={"member_id": member.pk}
        )

        def send_notification():
            send_email(
                to_email=[recipient],
                subject=f"{name}: Individuelle Vereinbarung offen",
                content=f"{member.get_display_name()} ({member.email}) hat eine individuelle Einlagenvereinbarung angefragt. "
                f"Gesamtbetrag und Zahlungsplan sind noch offen. Es wurde kein Einzug angelegt.\nEinlagenfall: {url}",
                attachments=[],
                cache=cache,
            )

        transaction.on_commit(send_notification, robust=True)
