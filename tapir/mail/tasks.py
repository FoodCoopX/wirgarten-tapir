from celery import shared_task

from tapir.mail.service.email_bounces import EmailBounces
from tapir.mail.service.email_dispatch import (
    ResolveAndCreateEmailDispatches,
    SendEmailBatch,
)


@shared_task
def resolve_segment_and_create_email_dispatches_task():
    ResolveAndCreateEmailDispatches.resolve_and_create()


@shared_task
def send_email_dispatch_batch_task():
    SendEmailBatch.send_email_dispatches()


@shared_task
def check_email_bounces():
    EmailBounces.check_for_bounces()
