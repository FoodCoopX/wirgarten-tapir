from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.bakery.views import (
    AvailableBreadsForDeliveryListView,
    ConfigurationParametersView,
    PickupListView,
    PreferenceSatisfactionMetricsView,
    PreferredBreadStatisticsView,
    SolverApplyView,
    SolverPreviewDetailView,
    SolverPreviewView,
)
from tapir.bakery.views_pdfs import (
    baking_list_pdf,
    distribution_list_pdf,
    pickup_list_pdf,
    pickup_lists_all_pdf,
)
from tapir.bakery.views_templates import (
    ChooseBreadsView,
    IngredientsLabelsBreadsView,
    ReportsView,
    WeeklyPlanBreadsView,
)
from tapir.bakery.viewsets import (
    BreadCapacityPickupLocationViewSet,
    BreadContentViewSet,
    BreadDeliveryViewSet,
    BreadLabelViewSet,
    BreadSpecificsPerDeliveryDayViewSet,
    BreadsPerPickupLocationPerWeekViewSet,
    BreadViewSet,
    IngredientViewSet,
    PreferredBreadViewSet,
    StoveSessionViewSet,
)

app_name = "bakery"

urlpatterns = [
    path(
        "available-breads-for-delivery/",
        AvailableBreadsForDeliveryListView.as_view(),
        name="breads-for-delivery-list",
    ),
    path("pickup-list/", PickupListView.as_view(), name="pickup-list"),
    path(
        "ingredients-labels-breads/",
        IngredientsLabelsBreadsView.as_view(),
        name="ingredients-labels-breads",
    ),
    path(
        "weekly-plan-breads/",
        WeeklyPlanBreadsView.as_view(),
        name="weekly-plan-breads",
    ),
    path("choose-breads/", ChooseBreadsView.as_view(), name="choose-breads"),
    path("reports/", ReportsView.as_view(), name="reports"),
    path(
        "api/bakery/solver/preview/", SolverPreviewView.as_view(), name="solver-preview"
    ),
    path(
        "api/bakery/solver/preview/detail/",
        SolverPreviewDetailView.as_view(),
        name="solver-preview-detail",
    ),
    path("api/bakery/solver/apply/", SolverApplyView.as_view(), name="solver-apply"),
    path(
        "metrics/satisfaction/",
        PreferenceSatisfactionMetricsView.as_view(),
        name="metrics-preference-satisfaction",
    ),
    # PDF exports
    path(
        "pdf/baking-list/<int:year>/<int:week>/<int:day>/",
        baking_list_pdf,
        name="baking_list_pdf",
    ),
    path(
        "pdf/distribution-list/<int:year>/<int:week>/<int:day>/",
        distribution_list_pdf,
        name="distribution_list_pdf",
    ),
    path(
        "pdf/pickup-list/<int:year>/<int:week>/<int:day>/<str:pickup_location_id>/",
        pickup_list_pdf,
        name="pickup_list_pdf",
    ),
    path(
        "pdf/pickup-lists-all/<int:year>/<int:week>/<int:day>/",
        pickup_lists_all_pdf,
        name="pdf_pickup_lists_all",
    ),
    path(
        "api/preferred-bread-statistics/",
        PreferredBreadStatisticsView.as_view(),
        name="preferred-bread-statistics",
    ),
    path(
        "api/configuration-parameters/",
        ConfigurationParametersView.as_view(),
        name="configuration-parameters",
    ),
]

router = DefaultRouter()
router.register(
    r"breads-list",
    BreadViewSet,
    basename="breads-list",
)
router.register(
    r"labels",
    BreadLabelViewSet,
    basename="labels",
)
router.register(
    r"ingredients",
    IngredientViewSet,
    basename="ingredients",
)
router.register(
    r"breadcontents",
    BreadContentViewSet,
    basename="breadcontents",
)
router.register(
    r"bread-capacity-pickup-location",
    BreadCapacityPickupLocationViewSet,
    basename="bread_capacity_pickup_location",
)

router.register(r"preferred-breads", PreferredBreadViewSet, basename="preferred-breads")
router.register(
    r"bread-deliveries",
    BreadDeliveryViewSet,
    basename="bread-deliveries",
)
router.register(
    r"stove-sessions",
    StoveSessionViewSet,
    basename="stove-sessions",
)
router.register(
    r"breads-per-pickup-location-per-week",
    BreadsPerPickupLocationPerWeekViewSet,
    basename="breads-per-pickup-location-per-week",
)
router.register(
    r"bread-specifics", BreadSpecificsPerDeliveryDayViewSet, basename="bread-specifics"
)


urlpatterns += router.urls
