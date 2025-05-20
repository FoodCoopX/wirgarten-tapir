import base64
import json
from typing import Dict

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.urls import reverse_lazy
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir import settings
from tapir.accounts.config import EMAIL_CHANGE_LINK_VALIDITY_MINUTES
from tapir.accounts.models import TapirUser, KeycloakUser, EmailChangeRequest
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
        url = reverse_lazy(
            "accounts:change_email_confirm", kwargs={"token": email_change_token}
        )
        verify_link = f"{settings.SITE_URL}{url}"

        TransactionalTrigger.fire_action(
            trigger_data=TransactionalTriggerData(
                key=Events.MEMBERAREA_CHANGE_EMAIL_INITIATE,
                recipient_id_in_base_queryset=user.id,
                token_data={"verify_link": verify_link},
            )
        )

        TransactionalTrigger.fire_action(
            trigger_data=TransactionalTriggerData(
                key=Events.MEMBERAREA_CHANGE_EMAIL_HINT,
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=new_email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                ),
            )
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
            trigger_data=TransactionalTriggerData(
                key=Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS,
                recipient_id_in_base_queryset=user.id,
            )
        )
