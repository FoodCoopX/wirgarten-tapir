import base64
import json

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.urls import reverse_lazy
from tapir.mail.models import (
    StaticSegmentRecipient,
    ExternalRecipient,
    ExternalRecipientConfirmation,
)
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir import settings
from tapir.accounts.config import EMAIL_CHANGE_LINK_VALIDITY_MINUTES
from tapir.accounts.models import TapirUser, KeycloakUser, EmailChangeRequest
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.core.services.mailman.mailing_list_address_mover import (
    MailingListAddressMover,
)
from tapir.core.services.member_extra_email_address_releaser import (
    MemberExtraEmailAddressReleaser,
)
from tapir.wirgarten.mail_events import Events
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
    def apply_mail_change(
        cls, user: TapirUser, new_email: str, actor: TapirUser | None, cache: dict
    ):
        old_email = user.email
        user.email = new_email
        user.username = new_email
        user.save()

        EmailChangeRequest.objects.filter(user_id=user.id).delete()

        # Clearing requests that are not related to this user but that are outdated
        link_validity = relativedelta(minutes=EMAIL_CHANGE_LINK_VALIDITY_MINUTES)
        EmailChangeRequest.objects.filter(
            created_at__lte=get_now(cache=cache) - link_validity
        ).delete()

        StaticSegmentRecipient.objects.filter(email=old_email).update(email=new_email)
        MemberExtraEmailAddressReleaser.release_address(address=new_email, actor=actor)
        cls._move_external_recipient(old_email=old_email, new_email=new_email)
        transaction.on_commit(
            lambda: MailingListAddressMover.move_subscriptions(
                old_email=old_email, new_email=new_email, cache=cache
            ),
            robust=True,
        )

        TransactionalTrigger.fire_action(
            trigger_data=TransactionalTriggerData(
                key=Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS,
                recipient_id_in_base_queryset=user.id,
            )
        )

        kc = KeycloakUserManager.get_keycloak_client()
        kc.update_user(
            user_id=user.keycloak_id,
            payload={
                "email": new_email,
            },
        )

    @staticmethod
    def _move_external_recipient(old_email: str, new_email: str):
        old_recipient = ExternalRecipient.objects.filter(email=old_email).first()
        if old_recipient is None:
            return

        new_recipient = ExternalRecipient.objects.filter(email=new_email).first()
        if new_recipient is None:
            old_recipient.email = new_email
            old_recipient.save()
            return

        ExternalRecipientConfirmation.objects.filter(
            external_recipient=old_recipient
        ).exclude(
            mail_category__in=ExternalRecipientConfirmation.objects.filter(
                external_recipient=new_recipient
            ).values("mail_category")
        ).update(
            external_recipient=new_recipient
        )
        old_recipient.delete()
