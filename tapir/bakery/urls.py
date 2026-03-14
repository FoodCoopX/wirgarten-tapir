from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.bakery.views import (
    AbhollisteView,
    AvailableBreadsForDeliveryListView,
    ConfigurationParametersView,
    PreferenceSatisfactionMetricsView,
    PreferredBreadStatisticsView,
    SolverApplyView,
    SolverPreviewDetailView,
    SolverPreviewView,
)
from tapir.bakery.views_pdfs import (
    abholliste_pdf,
    abhollisten_all_pdf,
    backliste_pdf,
    verteilliste_pdf,
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
    PreferredLabelViewSet,
    StoveSessionViewSet,
)

app_name = "bakery"

urlpatterns = [
    path(
        "available-breads-for-delivery/",
        AvailableBreadsForDeliveryListView.as_view(),
        name="breads-for-delivery-list",
    ),
    path("abholliste/", AbhollisteView.as_view(), name="abholliste"),
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
        "pdf/backliste/<int:year>/<int:week>/<int:day>/",
        backliste_pdf,
        name="backliste_pdf",
    ),
    path(
        "pdf/verteilliste/<int:year>/<int:week>/<int:day>/",
        verteilliste_pdf,
        name="verteilliste_pdf",
    ),
    path(
        "pdf/abholliste/<int:year>/<int:week>/<int:day>/<str:pickup_location_id>/",
        abholliste_pdf,
        name="abholliste_pdf",
    ),
    path(
        "pdf/abholliste-alle/<int:year>/<int:week>/<int:day>/",
        abhollisten_all_pdf,
        name="pdf_abhollisten_all",
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
router.register(
    r"preferred-labels",
    PreferredLabelViewSet,
    basename="preferred-labels",
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
