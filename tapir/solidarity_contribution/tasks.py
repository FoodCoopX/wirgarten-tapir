from celery import shared_task

from tapir.subscriptions.services.automatic_solidarity_contribution_renewal_service import (
    AutomaticSolidarityContributionRenewalService,
)


@shared_task
def automatic_solidarity_contribution_renewal():
    AutomaticSolidarityContributionRenewalService.renew_contributions_if_necessary()
