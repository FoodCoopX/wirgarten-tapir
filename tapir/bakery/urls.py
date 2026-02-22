from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.bakery.views import (
    AvailableBreadsForDeliveryListView,
)
from tapir.bakery.views_templates import (
    ChooseBreadsView,
    IngredientsLabelsBreadsView,
    ReportsView,
    WeeklyPlanBreadsView,
)
from tapir.bakery.viewsets import (
    BreadCapacityPickupStationViewSet,
    BreadContentViewSet,
    BreadDeliveryViewSet,
    BreadLabelViewSet,
    BreadViewSet,
    IngredientViewSet,
    PreferredLabelViewSet,
)

app_name = "bakery"

urlpatterns = [
    path(
        "available-breads-for-delivery/",
        AvailableBreadsForDeliveryListView.as_view(),
        name="breads-for-delivery-list",
    ),
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
    r"bread-capacity-pickup-station",
    BreadCapacityPickupStationViewSet,
    basename="bread_capacity_pickup_station",
)
router.register(
    r"preferred-labels",
    PreferredLabelViewSet,
    basename="preferred-labels",
)
router.register(
    r"bread-deliveries",
    BreadDeliveryViewSet,
    basename="bread-deliveries",
)


urlpatterns += router.urls
