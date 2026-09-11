import datetime
import logging

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.associations.apps import AssociationsConfig
from tapir.associations.models import AssociationMembership
from tapir.wirgarten.utils import get_today, format_date, get_now

logger = logging.getLogger(__name__)


@shared_task
def trigger_association_membership_ends_today_mails():
    cache = {}
    today = get_today(cache=cache)
    for membership in AssociationMembership.objects.filter(
        end_date__lte=today,
        end_date__gt=today - datetime.timedelta(days=14),
        membership_ended_mail_sent_on=None,
    ).select_related("type"):
        if (
            AssociationMembership.objects.filter(member_id=membership.member_id)
            .filter(Q(end_date__gt=today) | Q(end_date=None))
            .exists()
        ):
            continue
        with transaction.atomic():
            TransactionalTrigger.fire_action(
                trigger_data=TransactionalTriggerData(
                    key=AssociationsConfig.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY,
                    recipient_id_in_base_queryset=membership.member_id,
                    token_data={
                        "membership_type_name": membership.type.name,
                        "end_date_set_on": format_date(
                            membership.cancellation_ts.date()
                        ),
                    },
                )
            )
            membership.membership_ended_mail_sent_on = get_now(cache=cache)
            membership.save()
