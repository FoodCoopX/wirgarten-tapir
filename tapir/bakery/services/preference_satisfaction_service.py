from collections import defaultdict

from tapir.bakery.models import (
    Bread,
    BreadsPerPickupLocationPerWeek,
    PreferenceSatisfactionLogging,
    PreferredBread,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.utils.services.tapir_cache import TapirCache


class PreferenceSatisfactionService:
    """
    Simulates the pickup to work out how many members got a bread they wanted.

    Members are served in the order the deliveries come back; a member counts
    as satisfied when they had no favourites at all, or got one of them.
    """

    @classmethod
    def get_metrics(
        cls,
        year: int,
        delivery_week: int,
        delivery_day: int | None,
        cache: dict,
    ) -> dict:
        # The station and the joker status are derived; the service leaves
        # jokered slots out.
        deliveries_by_location = (
            BreadDeliveryContextService.get_deliveries_by_location_for_week(
                year=year,
                delivery_week=delivery_week,
                cache=cache,
                delivery_day=delivery_day,
            )
        )

        if not deliveries_by_location:
            return {"locations": []}

        deliveries = [d for ds in deliveries_by_location.values() for d in ds]
        location_ids = list(deliveries_by_location.keys())

        distribution_qs = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=delivery_week,
            pickup_location_id__in=location_ids,
        ).select_related("bread", "pickup_location")

        distributed_breads_lookup = {
            (d.bread_id, d.pickup_location_id): d.count for d in distribution_qs
        }

        bread_ids = set(d.bread_id for d in deliveries if d.bread_id)
        bread_ids.update(bread_id for bread_id, _ in distributed_breads_lookup.keys())
        bread_map = {b.id: b for b in Bread.objects.filter(id__in=bread_ids)}

        member_ids = [d.subscription.member_id for d in deliveries]
        preferred_breads_qs = PreferredBread.objects.filter(
            member_id__in=member_ids
        ).prefetch_related("breads")

        # member_id -> list of favorite bread ids (ordered)
        # Members NOT in this dict have no PreferredBread entry at all
        member_favorites = {}
        for pref in preferred_breads_qs:
            # .all() reads the prefetch cache; any other queryset method on a
            # prefetched related manager bypasses it and queries per member.
            member_favorites[pref.member_id] = [bread.id for bread in pref.breads.all()]

        location_metrics = []

        for location_id, location_deliveries in deliveries_by_location.items():
            pickup_location = TapirCache.get_pickup_location_by_id(
                cache=cache, pickup_location_id=location_id
            )

            # Available breads at this location (from solver)
            available_breads_count = {}
            bread_breakdown = defaultdict(lambda: {"count": 0, "directly_chosen": 0})

            for (bread_id, loc_id), count in distributed_breads_lookup.items():
                if loc_id == location_id:
                    available_breads_count[bread_id] = count
                    bread_breakdown[bread_id]["count"] = count

            total_deliveries = len(location_deliveries)
            directly_chosen_count = 0
            no_favorites_count = 0
            got_favorite_count = 0
            no_match_count = 0

            # Assignment log for debugging
            assignment_log = []

            # 1) Process directly chosen breads first
            for delivery in location_deliveries:
                if delivery.bread_id:
                    directly_chosen_count += 1

                    member = delivery.subscription.member
                    assignment_log.append(
                        {
                            "member_name": f"{member.first_name} {member.last_name}",
                            "member_id": str(member.id),
                            "status": "directly_chosen",
                            "assigned_bread_id": str(delivery.bread_id),
                            "assigned_bread_name": (
                                bread_map[delivery.bread_id].name
                                if delivery.bread_id in bread_map
                                else "?"
                            ),
                            "preferred_bread_names": [],
                        }
                    )

                    if delivery.bread_id in available_breads_count:
                        available_breads_count[delivery.bread_id] = max(
                            0, available_breads_count[delivery.bread_id] - 1
                        )

                    if delivery.bread_id in bread_breakdown:
                        bread_breakdown[delivery.bread_id]["directly_chosen"] += 1

            # 2) Process unassigned deliveries
            unassigned_deliveries = [d for d in location_deliveries if not d.bread_id]
            unassigned_deliveries.sort(
                key=lambda d: (
                    d.subscription.member.last_name or "",
                    d.subscription.member.first_name or "",
                )
            )

            for delivery in unassigned_deliveries:
                member = delivery.subscription.member

                # Member has no favorites set → everything is fine for them
                if member.id not in member_favorites:
                    no_favorites_count += 1
                    assignment_log.append(
                        {
                            "member_name": f"{member.first_name} {member.last_name}",
                            "member_id": str(member.id),
                            "status": "no_favorites",
                            "assigned_bread_id": None,
                            "assigned_bread_name": None,
                            "preferred_bread_names": [],
                        }
                    )
                    continue

                favorite_bread_ids = member_favorites[member.id]

                # Member has empty favorites list → same as no favorites
                if not favorite_bread_ids:
                    no_favorites_count += 1
                    assignment_log.append(
                        {
                            "member_name": f"{member.first_name} {member.last_name}",
                            "member_id": str(member.id),
                            "status": "no_favorites",
                            "assigned_bread_id": None,
                            "assigned_bread_name": None,
                            "preferred_bread_names": [],
                        }
                    )
                    continue

                preferred_names = [
                    bread_map[b_id].name if b_id in bread_map else "?"
                    for b_id in favorite_bread_ids
                ]

                # Try to assign first available favorite
                assigned = False
                for bread_id in favorite_bread_ids:
                    if (
                        bread_id in available_breads_count
                        and available_breads_count[bread_id] > 0
                    ):
                        got_favorite_count += 1
                        available_breads_count[bread_id] -= 1
                        assigned = True
                        assignment_log.append(
                            {
                                "member_name": f"{member.first_name} {member.last_name}",
                                "member_id": str(member.id),
                                "status": "got_favorite",
                                "assigned_bread_id": str(bread_id),
                                "assigned_bread_name": (
                                    bread_map[bread_id].name
                                    if bread_id in bread_map
                                    else "?"
                                ),
                                "preferred_bread_names": preferred_names,
                            }
                        )
                        break

                if not assigned:
                    no_match_count += 1
                    assignment_log.append(
                        {
                            "member_name": f"{member.first_name} {member.last_name}",
                            "member_id": str(member.id),
                            "status": "no_match",
                            "assigned_bread_id": None,
                            "assigned_bread_name": None,
                            "preferred_bread_names": preferred_names,
                        }
                    )

            # "Satisfied" = directly chosen + no favorites (happy with anything) + got a favorite
            satisfied_count = (
                directly_chosen_count + no_favorites_count + got_favorite_count
            )
            satisfied_percentage = (
                (satisfied_count / total_deliveries * 100)
                if total_deliveries > 0
                else 0.0
            )

            # Bread breakdown list (just count + directly_chosen now)
            bread_breakdown_list = []
            for bread_id, bd_data in bread_breakdown.items():
                if bd_data["count"] > 0:
                    bread_breakdown_list.append(
                        {
                            "bread_id": bread_id,
                            "bread_name": (
                                bread_map[bread_id].name
                                if bread_id in bread_map
                                else "Unknown"
                            ),
                            "count": bd_data["count"],
                            "directly_chosen": bd_data["directly_chosen"],
                        }
                    )

            bread_breakdown_list.sort(key=lambda x: x["bread_name"])

            location_metrics.append(
                {
                    "pickup_location_id": str(location_id),
                    "pickup_location_name": pickup_location.name,
                    "delivery_day": PickupLocationDeliveryDayService.get_delivery_day(
                        pickup_location_id=location_id, cache=cache
                    ),
                    "total_deliveries": total_deliveries,
                    "directly_chosen": directly_chosen_count,
                    "no_favorites": no_favorites_count,
                    "got_favorite": got_favorite_count,
                    "satisfied": satisfied_count,
                    "satisfied_percentage": round(satisfied_percentage, 1),
                    "no_match": no_match_count,
                    "bread_breakdown": bread_breakdown_list,
                    "assignment_log": assignment_log,
                }
            )

        location_metrics.sort(key=lambda x: x["pickup_location_name"])

        return {"locations": location_metrics}

    @classmethod
    def log_satisfaction(
        cls,
        year: int,
        delivery_week: int,
        delivery_day: int | None,
        cache: dict,
    ) -> int:
        """
        Persist how well the plan that was just saved matches what members want.

        Right after a solver run is the only moment the number means anything:
        it describes that distribution, and the next run for the same week
        replaces it.

        A station with no opening times has no delivery day, and the model has
        no column for that, so it is left out rather than logged under a
        made-up day.
        """
        metrics = cls.get_metrics(
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
            cache=cache,
        )
        loggable = [
            location
            for location in metrics["locations"]
            if location["delivery_day"] is not None
        ]
        if not loggable:
            return 0

        # Replace rather than update: the week's plan was just rewritten, and
        # a station may have dropped out of it entirely.
        PreferenceSatisfactionLogging.objects.filter(
            year=year,
            delivery_week=delivery_week,
            pickup_location_id__in=[
                location["pickup_location_id"] for location in loggable
            ],
        ).delete()
        PreferenceSatisfactionLogging.objects.bulk_create(
            [
                PreferenceSatisfactionLogging(
                    year=year,
                    delivery_week=delivery_week,
                    delivery_day=location["delivery_day"],
                    pickup_location_id=location["pickup_location_id"],
                    percentage_satisfied=location["satisfied_percentage"],
                )
                for location in loggable
            ]
        )
        return len(loggable)
