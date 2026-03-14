from collections import defaultdict

from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    Bread,
    BreadDelivery,
    BreadsPerPickupLocationPerWeek,
    PreferredBread,
)
from tapir.bakery.serializers import (
    AbhollisteResponseSerializer,
    AvailableBreadsForDeliveryListResponseSerializer,
    PreferenceSatisfactionResponseSerializer,
    SolverApplyRequestSerializer,
    SolverApplyResponseSerializer,
    SolverErrorSerializer,
    SolverPreviewDetailResponseSerializer,
    SolverPreviewRequestSerializer,
    SolverPreviewResponseSerializer,
    ToggleBreadRequestSerializer,
    ToggleBreadResponseSerializer,
)
from tapir.bakery.services.abholliste_service import AbhollisteService
from tapir.bakery.utils import parse_week_params
from tapir.configuration.parameter import get_parameter_value
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys


class AvailableBreadsForDeliveryListView(APIView):
    """
    Get or toggle breads for a specific year, week and day
    """

    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="Get breads for a delivery day",
        parameters=[
            OpenApiParameter(name="year", type=int, required=True),
            OpenApiParameter(name="delivery_week", type=int, required=True),
            OpenApiParameter(name="delivery_day", type=int, required=True),
        ],
        responses={200: AvailableBreadsForDeliveryListResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, delivery_day = result

        available_breads = (
            AvailableBreadsForDeliveryDay.objects.filter(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                bread__is_active=True,
            )
            .select_related("bread")
            .order_by("bread__name")
        )

        breads = [
            {"id": str(entry.bread.id), "name": entry.bread.name}
            for entry in available_breads
        ]

        return Response(
            {
                "year": year,
                "delivery_week": delivery_week,
                "delivery_day": delivery_day,
                "breads": breads,
            }
        )

    @extend_schema(
        summary="Toggle bread availability for a delivery day",
        request=ToggleBreadRequestSerializer,
        responses={200: ToggleBreadResponseSerializer},
    )
    def post(self, request):
        serializer = ToggleBreadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data["year"]
        delivery_week = data["delivery_week"]
        delivery_day = data["delivery_day"]
        bread_id = data["bread_id"]
        is_active = data["is_active"]

        try:
            bread = Bread.objects.get(id=bread_id)
        except Bread.DoesNotExist:
            return Response(
                {"error": "Bread not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if is_active:
            entry, created = AvailableBreadsForDeliveryDay.objects.get_or_create(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                bread=bread,
            )
            return Response(
                {
                    "success": True,
                    "created": created,
                    "bread_id": str(bread_id),
                }
            )
        else:
            deleted_count, _ = AvailableBreadsForDeliveryDay.objects.filter(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                bread=bread,
            ).delete()
            return Response(
                {
                    "success": True,
                    "deleted": deleted_count > 0,
                    "bread_id": str(bread_id),
                }
            )


class AbhollisteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Abholliste for a specific pickup location",
        description="Returns a list of members with their bread deliveries for a specific week and pickup location. "
        "Includes delivery counts and preferred bread indicators.",
        parameters=[
            OpenApiParameter(
                name="year",
                type=OpenApiTypes.INT,
                required=True,
            ),
            OpenApiParameter(
                name="delivery_week",
                type=OpenApiTypes.INT,
                required=True,
            ),
            OpenApiParameter(
                name="pickup_location_id",
                type=OpenApiTypes.STR,
                required=True,
            ),
        ],
        responses={200: AbhollisteResponseSerializer},
        tags=["bakery"],
    )
    def get(self, request):
        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, delivery_day = result

        pickup_location_id = request.query_params.get("pickup_location_id")

        data = AbhollisteService.get_abholliste(year, delivery_week, pickup_location_id)

        result = {
            "bread_names": data["bread_names"],
            "bread_totals": data["bread_totals"],
            "grand_total": data["grand_total"],
            "entries": [
                {
                    "member_id": entry["member_id"],
                    "display_name": entry["member_name"],
                    "total_breads": entry["total"],
                    "bread_counts": entry["bread_counts"],
                    "bread_preferred": entry["bread_preferred"],
                    "breads": entry["breads"],
                }
                for entry in data["entries"]
            ],
        }

        serializer = AbhollisteResponseSerializer(result)
        return Response(serializer.data)


class SolverPreviewView(APIView):
    """Run the solver once and cache all solutions. Returns summaries."""

    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="Run solver and preview multiple solutions",
        description=(
            "Runs the constraint solver once with multiple solution collection. "
            "Solutions are cached for 1 hour. Nothing is saved to the database yet."
        ),
        request=SolverPreviewRequestSerializer,
        responses={
            200: SolverPreviewResponseSerializer,
            400: SolverErrorSerializer,
            422: SolverErrorSerializer,
        },
        tags=["bakery"],
    )
    def post(self, request: Request) -> Response:
        from tapir.bakery.solver import collect_solver_input, solve_bread_planning_all

        serializer = SolverPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data["year"]
        delivery_week = data["delivery_week"]
        delivery_day = data.get("delivery_day")
        max_solutions = min(data.get("max_solutions", 5), 20)

        solver_input = collect_solver_input(year, delivery_week, delivery_day)
        if solver_input is None:
            return Response(
                {
                    "error": "Keine Daten gefunden (keine Brote, Lieferungen oder Abholstationen)."
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        results = solve_bread_planning_all(
            **solver_input,
            max_solutions=max_solutions,
        )

        if not results:
            return Response(
                {"error": "Keine Lösung gefunden. Bitte Daten prüfen."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Cache all solutions
        cache_key = f"solver_solutions_{year}_{delivery_week}_{delivery_day}"
        cache.set(cache_key, results, timeout=3600)

        # Build bread name map
        all_bread_ids: set = set()
        for r in results:
            all_bread_ids.update(r["bread_quantities"].keys())

        bread_names = dict(
            Bread.objects.filter(id__in=all_bread_ids).values_list("id", "name")
        )

        # Build summaries
        summaries = []
        for i, result in enumerate(results):
            quantities = []
            for b_id, qty in result["bread_quantities"].items():
                if qty > 0:
                    rem = result["remaining_quantities"].get(b_id, 0)
                    quantities.append(
                        {
                            "bread_id": str(b_id),
                            "bread_name": bread_names.get(b_id, "?"),
                            "total": qty,
                            "deliveries": qty - rem,
                            "remaining": rem,
                        }
                    )

            summaries.append(
                {
                    "index": i,
                    "total_baked": sum(result["bread_quantities"].values()),
                    "total_remaining": sum(result["remaining_quantities"].values()),
                    "sessions_used": len(result["stove_sessions"]),
                    "quantities": quantities,
                }
            )

        response_data = {
            "total_solutions": len(results),
            "solutions": summaries,
        }

        response_serializer = SolverPreviewResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.data)


class SolverPreviewDetailView(APIView):
    """Return full details of a cached solution (stove plan, distribution)."""

    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="Get full details of a cached solver solution",
        parameters=[
            OpenApiParameter(name="year", type=OpenApiTypes.INT, required=True),
            OpenApiParameter(
                name="delivery_week", type=OpenApiTypes.INT, required=True
            ),
            OpenApiParameter(
                name="delivery_day", type=OpenApiTypes.INT, required=False
            ),
            OpenApiParameter(
                name="solution_index", type=OpenApiTypes.INT, required=False
            ),
        ],
        responses={
            200: SolverPreviewDetailResponseSerializer,
            404: SolverErrorSerializer,
        },
        tags=["bakery"],
    )
    def get(self, request: Request) -> Response:
        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, delivery_day = result

        solution_index = int(request.query_params.get("solution_index", 0))

        cache_key = f"solver_solutions_{year}_{delivery_week}_{delivery_day}"
        results = cache.get(cache_key)

        if not results:
            return Response(
                {"error": "Keine gecachten Lösungen. Bitte Solver neu starten."},
                status=status.HTTP_404_NOT_FOUND,
            )

        solution_index = min(solution_index, len(results) - 1)
        result = results[solution_index]

        # Build bread name map
        all_bread_ids: set = set(result["bread_quantities"].keys())
        for key in result["distribution"]:
            if isinstance(key, tuple):
                all_bread_ids.add(key[0])

        bread_names = dict(
            Bread.objects.filter(id__in=all_bread_ids).values_list("id", "name")
        )
        location_names = dict(PickupLocation.objects.values_list("id", "name"))

        # Format quantities
        quantities = []
        for b_id, qty in result["bread_quantities"].items():
            if qty > 0:
                rem = result["remaining_quantities"].get(b_id, 0)
                quantities.append(
                    {
                        "bread_id": str(b_id),
                        "bread_name": bread_names.get(b_id, "?"),
                        "total": qty,
                        "deliveries": qty - rem,
                        "remaining": rem,
                    }
                )

        # Format stove sessions
        stove_sessions = []
        for i, session in enumerate(result["stove_sessions"]):
            layers = []
            for j, layer_info in enumerate(session):
                if layer_info is None:
                    layers.append({"layer": j + 1, "bread_name": None, "quantity": 0})
                else:
                    b_id, qty = layer_info
                    layers.append(
                        {
                            "layer": j + 1,
                            "bread_id": str(b_id),
                            "bread_name": bread_names.get(b_id, "?"),
                            "quantity": qty,
                        }
                    )
            stove_sessions.append({"session": i + 1, "layers": layers})

        # Format distribution
        distribution = []
        for key, count in result["distribution"].items():
            if count > 0:
                if isinstance(key, tuple):
                    b_id, loc_id = key
                else:
                    b_id, loc_id = str(key).split(",")
                distribution.append(
                    {
                        "bread_id": str(b_id),
                        "bread_name": bread_names.get(
                            b_id, bread_names.get(str(b_id), "?")
                        ),
                        "pickup_location_id": str(loc_id),
                        "pickup_location_name": location_names.get(
                            loc_id, location_names.get(str(loc_id), "?")
                        ),
                        "count": count,
                    }
                )

        response_data = {
            "solution_index": solution_index,
            "total_solutions": len(results),
            "quantities": quantities,
            "stove_sessions": stove_sessions,
            "distribution": distribution,
        }

        response_serializer = SolverPreviewDetailResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.data)


class SolverApplyView(APIView):
    """Save a specific cached solution to the database."""

    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="Apply a cached solver solution to the database",
        description=(
            "Takes a cached solution (from /solver/preview/) and saves it to the database. "
            "This replaces any existing distribution and stove session data for the given week/day."
        ),
        request=SolverApplyRequestSerializer,
        responses={
            200: SolverApplyResponseSerializer,
            404: SolverErrorSerializer,
        },
        tags=["bakery"],
    )
    def post(self, request: Request) -> Response:
        from tapir.bakery.solver import save_solution_to_db

        serializer = SolverApplyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data["year"]
        delivery_week = data["delivery_week"]
        delivery_day = data.get("delivery_day")
        solution_index = data.get("solution_index", 0)

        cache_key = f"solver_solutions_{year}_{delivery_week}_{delivery_day}"
        results = cache.get(cache_key)

        if not results:
            return Response(
                {"error": "Keine gecachten Lösungen. Bitte Solver neu starten."},
                status=status.HTTP_404_NOT_FOUND,
            )

        solution_index = min(solution_index, len(results) - 1)
        chosen = results[solution_index]

        save_solution_to_db(year, delivery_week, delivery_day, chosen)

        response_data = {
            "success": True,
            "solution_index": solution_index,
            "message": f"Lösung {solution_index + 1} von {len(results)} wurde gespeichert.",
        }

        response_serializer = SolverApplyResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.data)


@extend_schema(tags=["bakery"])
class PreferenceSatisfactionMetricsView(APIView):
    """
    Calculate preference satisfaction metrics from existing data.

    For each pickup location, counts how many deliveries can be "satisfied":
    - Directly chosen bread (hard constraint in solver) → satisfied
    - Member has no favorites set → satisfied (everything is fine for them)
    - Member has favorites → simulate pickup: first available favorite gets picked

    The remaining deliveries are "no match" (member has favorites but none available).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="year", type=int, required=True),
            OpenApiParameter(name="delivery_week", type=int, required=True),
            OpenApiParameter(name="delivery_day", type=int, required=False),
        ],
        responses={200: PreferenceSatisfactionResponseSerializer},
        description="Calculate preference satisfaction metrics for a given week. "
        "Simulates pickup: members choose their first available favorite bread.",
    )
    def get(self, request: Request) -> Response:

        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, delivery_day = result

        deliveries_qs = BreadDelivery.objects.filter(
            year=year,
            delivery_week=delivery_week,
        ).select_related(
            "pickup_location",
            "bread",
            "subscription__member",
        )

        deliveries = list(deliveries_qs)

        if delivery_day is not None:
            deliveries = [
                d for d in deliveries if d.pickup_location.delivery_day == delivery_day
            ]

        if not deliveries:
            return Response({"locations": []})

        location_ids = list(set(d.pickup_location_id for d in deliveries))

        distribution_qs = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=delivery_week,
            pickup_location_id__in=location_ids,
        ).select_related("bread", "pickup_location")

        distributed_breads_lookup = {
            (d.bread_id, d.pickup_location_id): d.count for d in distribution_qs
        }

        bread_map = {b.id: b for b in Bread.objects.all()}

        member_ids = [d.subscription.member_id for d in deliveries]
        preferred_breads_qs = PreferredBread.objects.filter(
            member_id__in=member_ids
        ).prefetch_related("breads")

        # member_id -> list of favorite bread ids (ordered)
        # Members NOT in this dict have no PreferredBread entry at all
        member_favorites = {}
        for pref in preferred_breads_qs:
            member_favorites[pref.member_id] = list(
                pref.breads.values_list("id", flat=True)
            )

        deliveries_by_location = defaultdict(list)
        for delivery in deliveries:
            deliveries_by_location[delivery.pickup_location_id].append(delivery)

        location_metrics = []

        for location_id, location_deliveries in deliveries_by_location.items():
            pickup_location = location_deliveries[0].pickup_location

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

            # 1) Process directly chosen breads first
            for delivery in location_deliveries:
                if delivery.bread_id:
                    directly_chosen_count += 1

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
                    continue

                favorite_bread_ids = member_favorites[member.id]

                # Member has empty favorites list → same as no favorites
                if not favorite_bread_ids:
                    no_favorites_count += 1
                    continue

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
                        break

                if not assigned:
                    no_match_count += 1

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
                    "delivery_day": pickup_location.delivery_day,
                    "total_deliveries": total_deliveries,
                    "directly_chosen": directly_chosen_count,
                    "no_favorites": no_favorites_count,
                    "got_favorite": got_favorite_count,
                    "satisfied": satisfied_count,
                    "satisfied_percentage": round(satisfied_percentage, 1),
                    "no_match": no_match_count,
                    "bread_breakdown": bread_breakdown_list,
                }
            )

        location_metrics.sort(key=lambda x: x["pickup_location_name"])

        return Response({"locations": location_metrics})


@extend_schema(tags=["bakery"])
class PreferredBreadStatisticsView(APIView):
    """
    Count how many members (with active BreadDelivery) prefer each bread type.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="year", type=int, required=True),
            OpenApiParameter(name="delivery_week", type=int, required=True),
            OpenApiParameter(name="delivery_day", type=int, required=False),
        ],
        responses={200: dict},
        description="Count preferred breads among members with active deliveries for the given week.",
    )
    def get(self, request: Request) -> Response:

        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, delivery_day = result

        # Get all members with deliveries this week
        deliveries_qs = BreadDelivery.objects.filter(
            year=year,
            delivery_week=delivery_week,
        ).select_related("pickup_location", "subscription__member")

        deliveries = list(deliveries_qs)

        if delivery_day is not None:
            deliveries = [
                d
                for d in deliveries
                if d.pickup_location and d.pickup_location.delivery_day == delivery_day
            ]

        # Unique members with deliveries
        member_ids = list(set(d.subscription.member_id for d in deliveries))
        total_members = len(member_ids)

        # Get preferred breads for these members
        preferred_qs = PreferredBread.objects.filter(
            member_id__in=member_ids
        ).prefetch_related("breads")

        members_with_preferences = 0
        members_without_preferences = 0
        bread_counts: dict[str, int] = {}
        bread_ids_to_names: dict = {}

        for pref in preferred_qs:
            bread_list = list(pref.breads.all())
            if bread_list:
                members_with_preferences += 1
                for bread in bread_list:
                    bread_ids_to_names[bread.id] = bread.name
                    bread_counts[bread.name] = bread_counts.get(bread.name, 0) + 1
            else:
                members_without_preferences += 1

        # Members with no PreferredBread entry at all
        members_with_pref_entry = set(p.member_id for p in preferred_qs)
        members_without_preferences += sum(
            1 for m_id in member_ids if m_id not in members_with_pref_entry
        )

        # Sort by count descending
        bread_statistics = sorted(
            [
                {
                    "bread_name": name,
                    "count": count,
                    "percentage": (
                        round(count / total_members * 100, 1)
                        if total_members > 0
                        else 0
                    ),
                }
                for name, count in bread_counts.items()
            ],
            key=lambda x: x["count"],
            reverse=True,
        )

        return Response(
            {
                "total_members": total_members,
                "members_with_preferences": members_with_preferences,
                "members_without_preferences": members_without_preferences,
                "breads": bread_statistics,
            }
        )


@extend_schema(tags=["bakery"])
class ConfigurationParametersView(APIView):
    """
    Get configuration parameters needed by the frontend.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get configuration parameters",
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {"type": "string"},
                    },
                },
            }
        },
    )
    def get(self, request: Request) -> Response:

        # Define which parameters to expose to the frontend
        exposed_parameters = [
            {
                "key": ParameterKeys.BAKERY_LAST_CHOOSING_DAY_BEFORE_BAKING_DAY,
                "description": "Days before baking day when members must choose breads",
            },
            {
                "key": ParameterKeys.BAKERY_BAKING_DAY_BEFORE_DELIVERY_DAY,
                "description": "Days before delivery day when baking happens",
            },
        ]

        parameters = []
        for param in exposed_parameters:
            try:
                value = get_parameter_value(param["key"])
                parameters.append(
                    {
                        "key": param["key"],
                        "value": str(value) if value is not None else "",
                    }
                )
            except Exception as e:
                # Log error but don't fail the entire request
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to get parameter {param['key']}: {e}")

        return Response(parameters)
