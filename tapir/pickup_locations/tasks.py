from celery import shared_task

from tapir.pickup_locations.services.member_pickup_location_cleaner import (
    MemberPickupLocationCleaner,
)
from tapir.wirgarten.utils import (
    get_today,
)


@shared_task
def clean_members_without_subscription_task():
    MemberPickupLocationCleaner.clean_members_without_subscription(
        reference_date=get_today(cache={}), dry_run=False
    )
