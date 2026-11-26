import logging

from celery import shared_task

from tapir.accounts.exceptions import VerificationEmailsAlreadySendingException
from tapir.accounts.models import TapirUser
from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.wirgarten.models import Member

LOG = logging.getLogger(__name__)


@shared_task
def send_verification_emails(member_ids: list[str], actor_id: str):
    members = list(
        Member.objects.filter(id__in=member_ids).order_by(
            "member_no", "last_name", "first_name"
        )
    )
    actor = TapirUser.objects.get(id=actor_id)
    try:
        failures = UnverifiedMembersService.send_verification_emails(
            members=members, actor=actor
        )
    except VerificationEmailsAlreadySendingException:
        LOG.error("Verification emails are already being sent, skipping this task")
        return
    UnverifiedMembersService.send_report(
        recipient=actor, member_count=len(members), failures=failures, cache={}
    )
