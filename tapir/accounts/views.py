import base64
import json

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.accounts.models import EmailChangeRequest, TapirUser
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.tapirmail import Events

# FIXME: this file has a dependency on tapir/wirgarten! Replace the send_email call as soon as the mail module is ready

EMAIL_CHANGE_LINK_VALIDITY_MINUTES = 24 * 60


@transaction.atomic
def change_email(request, **kwargs):
    data = json.loads(base64.b64decode(kwargs["token"]))
    user_id = data["user"]
    new_email = data["new_email"]
    matching_change_request = EmailChangeRequest.objects.filter(
        new_email=new_email, secret=data["secret"], user_id=user_id
    ).order_by("-created_at")

    link_validity = relativedelta(minutes=EMAIL_CHANGE_LINK_VALIDITY_MINUTES)
    now = timezone.now()
    if matching_change_request.exists() and now < (
        matching_change_request[0].created_at + link_validity
    ):
        # token is valid -> actually change email
        user = TapirUser.objects.get(id=user_id)
        orig_email = user.email
        user.change_email(new_email)

        # delete other change requests for this user
        EmailChangeRequest.objects.filter(user_id=user_id).delete()
        # delete expired change requests
        EmailChangeRequest.objects.filter(created_at__lte=now - link_validity).delete()

        TransactionalTrigger.fire_action(
            Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS,
            new_email,
        )
        cache = {}
        # send confirmation to old email address
        send_email(
            to_email=[orig_email],
            subject=_("Deine Email Adresse wurde geändert"),
            content=_(
                f"Hallo {user.first_name},<br/><br/>"
                f"deine Email Adresse wurde erfolgreich zu <strong>{new_email}</strong> geändert.<br/>"
                f"""Falls du das nicht warst, ändere bitte sofort dein Passwort im <a href="{settings.SITE_URL}" target="_blank">Mitgliederbereich</a> und kontaktiere uns indem du einfach auf diese Mail antwortest."""
                f"<br/><br/>Herzliche Grüße, dein WirGarten Team"
            ),
            cache=cache,
        )

        # FIXME: reference to wirgarten namespace!
        return HttpResponseRedirect(
            reverse_lazy("wirgarten:member_detail", kwargs={"pk": user.id})
            + "?email_changed=true"
        )

    return HttpResponseRedirect(reverse_lazy("link_expired"))
