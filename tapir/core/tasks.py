from celery import shared_task
from django.core.management import call_command

from tapir.core.services.mailman.former_member_list_unsubscriber import (
    FormerMemberListUnsubscriber,
)


@shared_task
def unsubscribe_former_members_from_mailing_lists():
    FormerMemberListUnsubscriber.unsubscribe_former_members(cache={})


@shared_task
def clear_expired_sessions():
    call_command("clearsessions")
