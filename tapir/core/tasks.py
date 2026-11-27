from celery import shared_task

from tapir.core.services.mailman.former_member_list_unsubscriber import (
    FormerMemberListUnsubscriber,
)


@shared_task
def unsubscribe_former_members_from_mailing_lists():
    FormerMemberListUnsubscriber.unsubscribe_former_members(cache={})
