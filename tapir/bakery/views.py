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
)
from tapir.bakery.serializers import (
    AvailableBreadsForDeliveryListResponseSerializer,
    BreadListSerializer,
    PickupListsResponseSerializer,
    PreferenceSatisfactionResponseSerializer,
    PreferredBreadStatisticsSerializer,
    SolverApplyRequestSerializer,
    SolverApplyResponseSerializer,
    SolverErrorSerializer,
    SolverPreviewDetailResponseSerializer,
    SolverPreviewRequestSerializer,
    SolverPreviewResponseSerializer,
    ToggleBreadRequestSerializer,
    ToggleBreadResponseSerializer,
)
from tapir.bakery.services.pickup_list_service import PickupListService
from tapir.bakery.solver_availability import (
    SOLVER_UNAVAILABLE_MESSAGE,
    is_solver_available,
)
from tapir.bakery.services.preference_satisfaction_service import (
    PreferenceSatisfactionService,
)
from tapir.bakery.services.preferred_bread_statistics_service import (
    PreferredBreadStatisticsService,
)
from tapir.bakery.utils import parse_week_params
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
            .prefetch_related("bread__labels", "bread__contents__ingredient")
            .order_by("bread__name")
        )

        # Through the serializer this endpoint advertises. Hand-building
        # {"id", "name"} here produced an object the generated client cannot
        # parse: contents is a required array on BreadList, and the client
        # maps over it without a null check.
        return Response(
            {
                "year": year,
                "delivery_week": delivery_week,
                "delivery_day": delivery_day,
                "breads": BreadListSerializer(
                    [entry.bread for entry in available_breads], many=True
                ).data,
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


class PickupListView(APIView):
    # pickup_location_id comes straight from the query string, and the
    # response is a station's member roster.
    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="Get pickup list for a specific pickup location",
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
                name="pickup_location_ids[]",
                type=OpenApiTypes.STR,
                many=True,
                required=False,
                description="One or more stations. Falls back to pickup_location_id.",
            ),
            OpenApiParameter(
                name="pickup_location_id",
                type=OpenApiTypes.STR,
                required=False,
            ),
        ],
        responses={200: PickupListsResponseSerializer},
        tags=["bakery"],
    )
    def get(self, request):
        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, _delivery_day = result

        pickup_location_ids = request.query_params.getlist("pickup_location_ids[]")
        if not pickup_location_ids:
            single = request.query_params.get("pickup_location_id")
            pickup_location_ids = [single] if single else []

        if not pickup_location_ids:
            return Response(
                {"error": "pickup_location_ids[] oder pickup_location_id ist nötig."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # One cache for the whole request: the week's deliveries are grouped
        # by station once, and every further station is answered out of that
        # grouping.
        cache = {}
        lists = [
            {
                "pickup_location_id": pickup_location_id,
                **PickupListService.get_pickup_list(
                    year, delivery_week, pickup_location_id, cache=cache
                ),
            }
            for pickup_location_id in pickup_location_ids
        ]

        return Response(PickupListsResponseSerializer({"lists": lists}).data)


SOLVER_CACHE_TIMEOUT_SECONDS = 3600


def _bread_names(bread_ids) -> dict:
    """Bread id -> name for the ids a solver result mentions, in one query."""
    return dict(Bread.objects.filter(id__in=bread_ids).values_list("id", "name"))


def _solver_cache_key(year, delivery_week, delivery_day) -> str:
    """
    One owner for the key. Preview writes it, detail and apply read it, and
    all three have to agree down to how delivery_day=None stringifies.
    """
    return f"solver_solutions_{year}_{delivery_week}_{delivery_day}"


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
        if not is_solver_available():
            return Response(
                {"error": SOLVER_UNAVAILABLE_MESSAGE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

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
                    "error": "Keine Daten gefunden (keine Brote, Lieferungen oder Abholstationen).",
                    "diagnostics": [],
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        solver_output = solve_bread_planning_all(
            **solver_input,
            max_solutions=max_solutions,
        )

        results = solver_output["solutions"]
        all_diagnostics = solver_output["diagnostics"]

        if not results:
            return Response(
                {
                    "error": "Keine Lösung gefunden. Bitte Daten prüfen.",
                    "diagnostics": all_diagnostics,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Cache all solutions
        cache_key = _solver_cache_key(year, delivery_week, delivery_day)
        cache.set(cache_key, results, timeout=SOLVER_CACHE_TIMEOUT_SECONDS)

        all_bread_ids: set = set()
        for r in results:
            all_bread_ids.update(r["bread_quantities"].keys())
        bread_names = _bread_names(all_bread_ids)

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
            "diagnostics": all_diagnostics,
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

        try:
            solution_index = int(request.query_params.get("solution_index", 0))
        except (TypeError, ValueError):
            return Response(
                {"error": "solution_index muss eine Zahl sein."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = _solver_cache_key(year, delivery_week, delivery_day)
        results = cache.get(cache_key)

        if not results:
            return Response(
                {"error": "Keine gecachten Lösungen. Bitte Solver neu starten."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Clamped at both ends: a negative value would otherwise reach
        # Python's negative indexing and select a different solution.
        solution_index = max(0, min(solution_index, len(results) - 1))
        result = results[solution_index]

        all_bread_ids: set = set(result["bread_quantities"].keys())
        for key in result["distribution"]:
            if isinstance(key, tuple):
                all_bread_ids.add(key[0])
        bread_names = _bread_names(all_bread_ids)
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
        if not is_solver_available():
            return Response(
                {"error": SOLVER_UNAVAILABLE_MESSAGE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        from tapir.bakery.solver import save_solution_to_db

        serializer = SolverApplyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data["year"]
        delivery_week = data["delivery_week"]
        delivery_day = data.get("delivery_day")
        solution_index = data.get("solution_index", 0)

        cache_key = _solver_cache_key(year, delivery_week, delivery_day)
        results = cache.get(cache_key)

        if not results:
            return Response(
                {"error": "Keine gecachten Lösungen. Bitte Solver neu starten."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Clamped at both ends: a negative value would otherwise reach
        # Python's negative indexing and apply a different solution.
        solution_index = max(0, min(solution_index, len(results) - 1))
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

    # Returns member names, ids and bread preferences for the whole co-op.
    permission_classes = [IsAuthenticated, HasCoopManagePermission]

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

        return Response(
            PreferenceSatisfactionService.get_metrics(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                cache={},
            )
        )


@extend_schema(tags=["bakery"])
class PreferredBreadStatisticsView(APIView):
    """
    Count how many members (with active BreadDelivery) prefer each bread type.
    """

    # Its only consumer is DashboardPreferredBreadStats on the admin
    # dashboard, which already requires this permission.
    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="year", type=int, required=True),
            OpenApiParameter(name="delivery_week", type=int, required=True),
            OpenApiParameter(name="delivery_day", type=int, required=False),
        ],
        responses={200: PreferredBreadStatisticsSerializer},
        description="Count preferred breads among members with active deliveries for the given week.",
    )
    def get(self, request: Request) -> Response:
        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, delivery_day = result

        return Response(
            PreferredBreadStatisticsService.get_statistics(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                cache={},
            )
        )
