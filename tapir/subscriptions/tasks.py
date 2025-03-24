from celery import shared_task

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)


@shared_task
def automatic_subscription_renewal():
    AutomaticSubscriptionRenewalService.renew_subscriptions_if_necessary()
