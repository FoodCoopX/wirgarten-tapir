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
)
from tapir.bakery.serializers import (
    AbhollisteEntrySerializer,
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
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.wirgarten.models import PickupLocation


class AvailableBreadsForDeliveryListView(APIView):
    """
    Get or toggle breads for a specific year, week and day
    """

    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="Get breads for a delivery day",
        parameters=[
            OpenApiParameter(name="year", type=int, required=True),
            OpenApiParameter(name="week", type=int, required=True),
            OpenApiParameter(name="day", type=int, required=True),
        ],
        responses={200: AvailableBreadsForDeliveryListResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        year = request.query_params.get("year")
        week = request.query_params.get("week")
        day = request.query_params.get("day")

        if not all([year, week, day]):
            return Response(
                {"error": "Missing parameters. Required: year, week, day"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year_int = int(year)
            week_int = int(week)
            day_int = int(day)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid year, week or day format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        available_breads = (
            AvailableBreadsForDeliveryDay.objects.filter(
                year=year_int,
                delivery_week=week_int,
                delivery_day=day_int,
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
            {"year": year_int, "week": week_int, "day": day_int, "breads": breads}
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
        week = data["week"]
        day = data["day"]
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
                delivery_week=week,
                delivery_day=day,
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
                delivery_week=week,
                delivery_day=day,
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
        description="Returns a list of members with their bread deliveries for a specific week, day, and pickup location. "
        "Members are sorted by display name (pseudonym or 'L., FirstName' format).",
        parameters=[
            OpenApiParameter(
                name="year",
                type=OpenApiTypes.INT,
                required=True,
            ),
            OpenApiParameter(
                name="week",
                type=OpenApiTypes.INT,
                required=True,
            ),
            OpenApiParameter(
                name="pickup_location_id",
                type=OpenApiTypes.STR,
                required=True,
            ),
        ],
        responses={
            200: AbhollisteEntrySerializer(many=True),
        },
        tags=["bakery"],
    )
    def get(self, request):

        year = int(request.query_params.get("year"))
        week = int(request.query_params.get("week"))
        pickup_location_id = request.query_params.get("pickup_location_id")

        deliveries = BreadDelivery.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id=pickup_location_id,
        ).select_related(
            "subscription__member",
            "bread",
            "pickup_location",
        )

        members_data = {}
        for delivery in deliveries:
            member = delivery.subscription.member
            member_id = str(member.id)

            if member_id not in members_data:
                pseudonym = getattr(member, "pseudonym", None)

                if pseudonym:
                    display_name = pseudonym
                else:
                    last_name = member.last_name if hasattr(member, "last_name") else ""
                    first_name = (
                        member.first_name if hasattr(member, "first_name") else ""
                    )

                    if last_name:
                        display_name = f"{last_name[0]}., {first_name}"
                    else:
                        display_name = first_name or "Unbekannt"

                members_data[member_id] = {
                    "member_id": member_id,
                    "display_name": display_name,
                    "total_breads": 0,
                    "breads": [],
                }

            members_data[member_id]["total_breads"] += 1
            members_data[member_id]["breads"].append(
                {
                    "delivery_id": str(delivery.id),
                    "bread_name": delivery.bread.name if delivery.bread else None,
                }
            )

        result = sorted(members_data.values(), key=lambda x: x["display_name"].lower())

        serializer = AbhollisteEntrySerializer(result, many=True)
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
        max_solutions = min(data.get("max_solutions", 3), 20)

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
        try:
            year = int(request.query_params["year"])
            delivery_week = int(request.query_params["delivery_week"])
            delivery_day_param = request.query_params.get("delivery_day")
            delivery_day = (
                int(delivery_day_param) if delivery_day_param is not None else None
            )
            solution_index = int(request.query_params.get("solution_index", 0))
        except (ValueError, TypeError, KeyError) as e:
            return Response(
                {"error": f"Ungültiges Parameterformat: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        from tapir.bakery.models import (
            Bread,
            BreadDelivery,
            PreferredBread,
        )

        year = request.query_params.get("year")
        delivery_week = request.query_params.get("delivery_week")
        delivery_day_param = request.query_params.get("delivery_day")

        try:
            year = int(year)
            delivery_week = int(delivery_week)
            delivery_day = int(delivery_day_param) if delivery_day_param else None
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid parameter format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                            "bread_name": bread_map[bread_id].name
                            if bread_id in bread_map
                            else "Unknown",
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
