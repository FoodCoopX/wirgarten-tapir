import datetime
import logging

from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import Member

LOG = logging.getLogger(__name__)


class MemberPickupLocationCleaner:
    @classmethod
    def clean_members_without_subscription(
        cls, reference_date: datetime.date, dry_run: bool
    ):
        cache = {}

        for member in Member.objects.all():
            cls._clean_member_pickup_location_if_necessary(
                member=member,
                cache=cache,
                reference_date=reference_date,
                dry_run=dry_run,
            )

    @classmethod
    def _clean_member_pickup_location_if_necessary(
        cls, member: Member, cache: dict, reference_date: datetime.date, dry_run: bool
    ):
        if not cls._should_clean_pickup_location(
            member=member, cache=cache, reference_date=reference_date
        ):
            return

        LOG.info(f"Cleaning pickup location for {member}")
        if dry_run:
            print(member)
            return

        MemberPickupLocationSetter.link_member_to_pickup_location(
            pickup_location_id=None,
            member=member,
            cache=cache,
            actor=None,
            valid_from=reference_date,
        )

    @classmethod
    def _should_clean_pickup_location(
        cls,
        member: Member,
        reference_date: datetime.date,
        cache: dict,
    ):
        return cls._does_member_have_an_active_or_future_pickup_location(
            member=member, reference_date=reference_date, cache=cache
        ) and (
            not cls._does_member_have_at_least_one_delivered_subscription(
                member=member, reference_date=reference_date, cache=cache
            )
        )

    @classmethod
    def _does_member_have_an_active_or_future_pickup_location(
        cls,
        member: Member,
        reference_date: datetime.date,
        cache: dict,
    ):
        member_pickup_location_objects = (
            MemberPickupLocationGetter.get_member_pickup_locations_objects_by_member_id(
                cache=cache
            ).get(member.id, [])
        )
        if len(member_pickup_location_objects) == 0:
            return False

        if member_pickup_location_objects[0].valid_from > reference_date:
            return True

        return member_pickup_location_objects[0].pickup_location is not None

    @classmethod
    def _does_member_have_at_least_one_delivered_subscription(
        cls,
        member: Member,
        reference_date: datetime.date,
        cache: dict,
    ):
        subscriptions = TapirCache.get_active_and_future_subscriptions_by_member_id(
            cache=cache, reference_date=reference_date
        ).get(member.id, [])

        return any(
            subscription.product.type.delivery_cycle != NO_DELIVERY[0]
            for subscription in subscriptions
        )
