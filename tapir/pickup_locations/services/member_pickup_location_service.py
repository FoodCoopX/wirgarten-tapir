import datetime
from typing import Dict, Set, List

from django.db.models import QuerySet, OuterRef, Subquery

from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import Member, MemberPickupLocation, PickupLocation


class MemberPickupLocationService:
    ANNOTATION_CURRENT_PICKUP_LOCATION_ID = "current_pickup_location_id"

    @classmethod
    def annotate_member_queryset_with_pickup_location_at_date(
        cls, queryset: QuerySet[Member], reference_date: datetime.date
    ) -> QuerySet[Member]:
        current_member_pickup_location = (
            MemberPickupLocation.objects.filter(
                member=OuterRef("id"), valid_from__lte=reference_date
            )
            .order_by("-valid_from")
            .values("pickup_location_id")[:1]
        )

        return queryset.annotate(
            **{
                cls.ANNOTATION_CURRENT_PICKUP_LOCATION_ID: Subquery(
                    current_member_pickup_location
                )
            }
        )

    @classmethod
    def get_member_pickup_location_id(
        cls, member: Member, reference_date: datetime.date
    ) -> int | None:
        if not hasattr(member, cls.ANNOTATION_CURRENT_PICKUP_LOCATION_ID):
            member = cls.annotate_member_queryset_with_pickup_location_at_date(
                Member.objects.filter(id=member.id), reference_date
            ).get()

        return getattr(member, cls.ANNOTATION_CURRENT_PICKUP_LOCATION_ID)

    @classmethod
    def get_members_ids_at_pickup_location(
        cls,
        pickup_location: PickupLocation,
        reference_date: datetime.date,
        cache: Dict,
    ) -> Set[str]:
        def build_if_cache_miss():
            members_at_pickup_location = set()
            for (
                member_id,
                member_pickup_locations,
            ) in cls.get_member_pickup_locations_objects_by_member_id(cache).items():
                member_pickup_locations = [
                    member_pickup_location
                    for member_pickup_location in member_pickup_locations
                    if member_pickup_location.valid_from <= reference_date
                ]
                if len(member_pickup_locations) == 0:
                    continue
                member_pickup_locations.sort(
                    key=lambda member_pickup_location: member_pickup_location.valid_from
                )
                if member_pickup_locations[-1].pickup_location_id == pickup_location.id:
                    members_at_pickup_location.add(member_id)
            return members_at_pickup_location

        cache_for_pickup_location = get_from_cache_or_compute(
            cache, pickup_location, lambda: {}
        )

        members_at_date = get_from_cache_or_compute(
            cache_for_pickup_location, "members_at_date", lambda: {}
        )

        return get_from_cache_or_compute(
            members_at_date, reference_date, build_if_cache_miss
        )

    @classmethod
    def get_member_pickup_locations_objects_by_member_id(
        cls, cache: Dict
    ) -> Dict[str, List[MemberPickupLocation]]:
        def build_if_cache_miss():
            member_pickup_locations = {}
            for member_pickup_location in MemberPickupLocation.objects.order_by(
                "valid_from"
            ):
                if member_pickup_location.member_id not in member_pickup_locations:
                    member_pickup_locations[member_pickup_location.member_id] = []
                member_pickup_locations[member_pickup_location.member_id].append(
                    member_pickup_location
                )
            return member_pickup_locations

        return get_from_cache_or_compute(
            cache, "member_pickup_locations_objects_by_member_id", build_if_cache_miss
        )

    @classmethod
    def get_member_pickup_location_id_from_cache(
        cls, member_id: str, reference_date: datetime.date, cache: Dict
    ):
        temp = cls.get_member_pickup_locations_objects_by_member_id(cache)
        if member_id not in temp:
            return None

        member_pickup_location_objects = temp[member_id]
        if len(member_pickup_location_objects) == 1:
            return member_pickup_location_objects[0].pickup_location_id

        for member_pickup_location_object in member_pickup_location_objects:
            if member_pickup_location_object.valid_from <= reference_date:
                return member_pickup_location_object.pickup_location_id

        return None
