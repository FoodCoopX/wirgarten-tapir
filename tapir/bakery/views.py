from django.core.cache import cache
from django.core.exceptions import ValidationError
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
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
    CopyWeekSettingsRequestSerializer,
    CopyWeekSettingsResponseSerializer,
    DeliveryDaysResponseSerializer,
    DirectOrderLimitsResponseSerializer,
    PickupListsResponseSerializer,
    PickupLocationsByDeliveryDayResponseSerializer,
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
    WeekSettingsSourcesResponseSerializer,
)
from tapir.bakery.services.bread_choice_deadline_service import (
    BreadChoiceDeadlineService,
)
from tapir.bakery.services.direct_order_limit_service import (
    DirectOrderLimitService,
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
from tapir.bakery.services.weekly_plan_service import WeeklyPlanService
from tapir.bakery.services.weekly_plan_validator import WeeklyPlanValidator
from tapir.bakery.utils import parse_week_params
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.pickup_locations.services.public_pickup_locations_provider import (
    PublicPickupLocationProvider,
)
from tapir.utils.services.tapir_cache import TapirCache
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
            .select_related("bread", "bread__group")
            .prefetch_related("bread__labels", "bread__contents__ingredient")
            .order_by("bread__name")
        )

        return Response(
            {
                "year": year,
                "delivery_week": delivery_week,
                "delivery_day": delivery_day,
                "delivery_day_is_over": delivery_day is not None
                and BreadChoiceDeadlineService.is_delivery_day_over(
                    year, delivery_week, delivery_day, cache={}
                ),
                "breads": BreadListSerializer(
                    [entry.bread for entry in available_breads], many=True
                ).data,
            }
        )

    @extend_schema(
        summary="Toggle bread availability for a delivery day",
        description=(
            "Switching a bread off clears the members' choices of it for that "
            "day. With dry_run, only counts them. A day that is over can no "
            "longer be changed."
        ),
        request=ToggleBreadRequestSerializer,
        responses={
            200: ToggleBreadResponseSerializer,
            400: OpenApiResponse(
                description="Validation errors, or the delivery day is over"
            ),
            404: OpenApiResponse(description="Bread not found"),
        },
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

        cache = {}
        try:
            WeeklyPlanValidator.validate_set_bread_baked(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                cache=cache,
            )
        except ValidationError as error:
            return Response(
                {"error": error.message}, status=status.HTTP_400_BAD_REQUEST
            )

        result = WeeklyPlanService.set_bread_baked(
            bread_id=bread.id,
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
            is_baked=is_active,
            cache=cache,
            dry_run=data["dry_run"],
        )
        response = {"success": True, "bread_id": str(bread_id)}
        if data["dry_run"]:
            response["cleared_choices"] = result.cleared_choices
        elif is_active:
            response["created"] = result.created
        else:
            response["deleted"] = result.deleted
            response["cleared_choices"] = result.cleared_choices
        return Response(response)


class PickupListView(APIView):
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
    return dict(Bread.objects.filter(id__in=bread_ids).values_list("id", "name"))


def _solver_cache_key(year, delivery_week, delivery_day) -> str:
    # v2: a stove layer is a list of (bread_id, pieces) since breads of a
    # group can share one, so solutions cached in the old shape are not read.
    return f"solver_solutions_v2_{year}_{delivery_week}_{delivery_day}"


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

        cache_key = _solver_cache_key(year, delivery_week, delivery_day)
        cache.set(cache_key, results, timeout=SOLVER_CACHE_TIMEOUT_SECONDS)

        all_bread_ids: set = set()
        for r in results:
            all_bread_ids.update(r["bread_quantities"].keys())
        bread_names = _bread_names(all_bread_ids)

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

        solution_index = max(0, min(solution_index, len(results) - 1))
        result = results[solution_index]

        all_bread_ids: set = set(result["bread_quantities"].keys())
        for key in result["distribution"]:
            if isinstance(key, tuple):
                all_bread_ids.add(key[0])
        bread_names = _bread_names(all_bread_ids)
        location_names = dict(PickupLocation.objects.values_list("id", "name"))

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

        # One entry per bread on a layer, like the StoveSession rows: the
        # breads of a group sharing a layer repeat its number.
        stove_sessions = []
        for i, session in enumerate(result["stove_sessions"]):
            layers = []
            for j, breads_on_layer in enumerate(session):
                if not breads_on_layer:
                    layers.append({"layer": j + 1, "bread_name": None, "quantity": 0})
                for b_id, qty in breads_on_layer:
                    layers.append(
                        {
                            "layer": j + 1,
                            "bread_id": str(b_id),
                            "bread_name": bread_names.get(b_id, "?"),
                            "quantity": qty,
                        }
                    )
            stove_sessions.append({"session": i + 1, "layers": layers})

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


@extend_schema(tags=["bakery"])
class DeliveryDaysView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get distinct list of delivery days",
        description="Returns the earliest delivery day per pickup location, 0=Montag.",
        responses={200: DeliveryDaysResponseSerializer},
    )
    def get(self, request):
        delivery_days = TapirCache.get_delivery_day_by_pickup_location_id(cache={})
        return Response({"days": sorted(set(delivery_days.values()))})


@extend_schema(tags=["bakery"])
class PickupLocationsByDeliveryDayView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get pickup locations filtered by delivery day",
        parameters=[
            OpenApiParameter(
                name="day_of_week",
                type=int,
                description="Day of week, 0=Montag to 6=Sonntag",
                required=True,
            )
        ],
        responses={200: PickupLocationsByDeliveryDayResponseSerializer},
    )
    def get(self, request):
        try:
            day_of_week = int(request.query_params.get("day_of_week"))
        except (TypeError, ValueError):
            return Response(
                {"error": "day_of_week must be a number (0-6)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache = {}
        pickup_location_ids = (
            PickupLocationDeliveryDayService.get_pickup_location_ids_for_delivery_day(
                day=day_of_week, cache=cache
            )
        )
        pickup_locations = (
            PublicPickupLocationProvider.get_pickup_locations_available_for_members(
                cache=cache
            ).filter(id__in=pickup_location_ids)
        )

        return Response(
            {
                "pickup_locations": [
                    {"id": pickup_location.id, "name": pickup_location.name}
                    for pickup_location in pickup_locations
                ]
            }
        )


@extend_schema(tags=["bakery"])
class DirectOrderLimitsView(APIView):
    """
    What members may order directly of each bread on one delivery day. The
    percentages are saved through the bread specifics bulk update.
    """

    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="Get the direct-order limits of every bread baked on a delivery day",
        parameters=[
            OpenApiParameter(name="year", type=int, required=True),
            OpenApiParameter(name="delivery_week", type=int, required=True),
            OpenApiParameter(name="delivery_day", type=int, required=True),
        ],
        responses={200: DirectOrderLimitsResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, delivery_day = result
        if delivery_day is None:
            return Response(
                {"error": "Missing required parameter: delivery_day"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limits = DirectOrderLimitService.get_limits_for_day(
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
            cache={},
        )
        return Response(
            DirectOrderLimitsResponseSerializer(
                {
                    "breads": list(limits.breads.values()),
                    "groups": list(limits.groups.values()),
                }
            ).data
        )


@extend_schema(tags=["bakery"])
class CopyWeekSettingsView(APIView):
    """Copy an earlier week's bread plan into a week, see WeeklyPlanService."""

    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="List the earlier weeks whose bread plan can be copied into a week",
        description="Weeks before the given one that bake an active bread, latest first.",
        parameters=[
            OpenApiParameter(name="year", type=int, required=True),
            OpenApiParameter(name="delivery_week", type=int, required=True),
        ],
        responses={200: WeekSettingsSourcesResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        result = parse_week_params(request.query_params)
        if isinstance(result, Response):
            return result

        year, delivery_week, _ = result
        sources = WeeklyPlanService.get_source_weeks(year, delivery_week, cache={})
        return Response(
            WeekSettingsSourcesResponseSerializer({"sources": sources}).data
        )

    @extend_schema(
        summary="Copy the bread plan and day settings of an earlier week into a week",
        description=(
            "Replaces, on each delivery day of the target week that is not "
            "over, the breads baked and their day settings with the source "
            "week's, and clears members' choices of breads no longer baked. "
            "With dry_run, only says what it would do."
        ),
        request=CopyWeekSettingsRequestSerializer,
        responses={
            200: CopyWeekSettingsResponseSerializer,
            400: OpenApiResponse(
                description=(
                    "Validation errors: a week that does not exist, or a "
                    "source week that is not before the target week or bakes "
                    "no active bread"
                )
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = CopyWeekSettingsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            WeeklyPlanValidator.validate_copy_week(
                source_year=data["source_year"],
                source_week=data["source_week"],
                target_year=data["target_year"],
                target_week=data["target_week"],
            )
        except ValidationError as error:
            return Response(
                {"error": error.message}, status=status.HTTP_400_BAD_REQUEST
            )

        result = WeeklyPlanService.copy_week(
            source_year=data["source_year"],
            source_week=data["source_week"],
            target_year=data["target_year"],
            target_week=data["target_week"],
            cache={},
            dry_run=data["dry_run"],
        )
        return Response(CopyWeekSettingsResponseSerializer(result).data)
