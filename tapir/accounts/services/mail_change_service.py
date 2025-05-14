import base64
import json
from typing import Dict

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir import settings
from tapir.accounts.config import EMAIL_CHANGE_LINK_VALIDITY_MINUTES
from tapir.accounts.models import TapirUser, KeycloakUser, EmailChangeRequest
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.tapirmail import Events
from tapir.wirgarten.utils import get_now


class MailChangeService:
    @classmethod
    @transaction.atomic
    def start_email_change_process(
        cls, user: KeycloakUser, new_email: str, orig_email: str
    ):
        EmailChangeRequest.objects.filter(user_id=user.id).delete()
        email_change_request = EmailChangeRequest.objects.create(
            new_email=new_email, user_id=user.id
        )
        email_change_token = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "new_email": email_change_request.new_email,
                    "secret": email_change_request.secret,
                    "user": email_change_request.user_id,
                }
            ).encode()
        ).decode()
        verify_link = f"{settings.SITE_URL}{reverse_lazy('change_email_confirm', kwargs={'token': email_change_token})}"

        TransactionalTrigger.fire_action(
            key=Events.MEMBERAREA_CHANGE_EMAIL_INITIATE,
            recipient_email=orig_email,
            token_data={"verify_link": verify_link},
        )

        TransactionalTrigger.fire_action(
            key=Events.MEMBERAREA_CHANGE_EMAIL_HINT,
            recipient_email=orig_email,
            recipient_email_override=new_email,
        )

        cache = {}
        send_email(
            to_email=[orig_email],
            subject=_("Änderung deiner Email-Adresse"),
            content=f"Hallo {user.first_name},<br/><br/>"
            f"du hast gerade die Email Adresse für deinen WirGarten Account geändert.<br/><br/>"
            f"Bitte klicke den folgenden Link um die Änderung zu bestätigen:<br/>"
            f"""<a target="_blank", href="{verify_link}"><strong>Email Adresse bestätigen</strong></a><br/><br/>"""
            f"Falls du das nicht warst, kannst du diese Mail einfach löschen oder ignorieren."
            f"<br/><br/>Grüße, dein WirGarten Team",
            cache=cache,
        )

    @classmethod
    @transaction.atomic
    def apply_mail_change(cls, user: TapirUser, new_email: str, cache: Dict):
        # token is valid -> actually change email
        orig_email = user.email
        user.change_email(new_email)

        # delete other change requests for this user
        EmailChangeRequest.objects.filter(user_id=user.id).delete()
        # delete expired change requests
        link_validity = relativedelta(minutes=EMAIL_CHANGE_LINK_VALIDITY_MINUTES)
        EmailChangeRequest.objects.filter(
            created_at__lte=get_now(cache=cache) - link_validity
        ).delete()

        TransactionalTrigger.fire_action(
            key=Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS,
            recipient_email=new_email,
        )
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
