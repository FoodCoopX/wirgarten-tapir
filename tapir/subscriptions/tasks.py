from celery import shared_task

from tapir.subscriptions.services.automatic_confirmation_manager import (
    AutomaticConfirmationManager,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)


@shared_task
def automatic_subscription_renewal():
    AutomaticSubscriptionRenewalService.renew_subscriptions_if_necessary()


@shared_task
def automatic_confirmation_subscriptions_and_share_purchases():
    AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()
