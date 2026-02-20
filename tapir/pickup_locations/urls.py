from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.pickup_locations import views

app_name = "pickup_locations"
urlpatterns = [
    path(
        "api/pickup_location_capacities",
        views.PickupLocationCapacitiesView.as_view(),
        name="pickup_location_capacities",
    ),
    path(
        "api/pickup_location_capacity_evolution",
        views.PickupLocationCapacityEvolutionView.as_view(),
        name="pickup_location_capacity_evolution",
    ),
    path(
        "api/pickup_location_capacity_check",
        views.PickupLocationCapacityCheckApiView.as_view(),
        name="pickup_location_capacity_check",
    ),
    path(
        "api/get_member_pickup_location",
        views.GetMemberPickupLocationApiView.as_view(),
        name="get_member_pickup_location",
    ),
    path(
        "api/change_member_pickup_location",
        views.ChangeMemberPickupLocationApiView.as_view(),
        name="change_member_pickup_location",
    ),
    path(
        "api/delivery_days",
        views.DeliveryDaysView.as_view(),
        name="delivery_days",
    ),
    path(
        "api/pickup_locations_by_delivery_day",
        views.PickupStationsByDeliveryDayView.as_view(),
        name="pickup_locations_by_delivery_day",
    ),
]

router = DefaultRouter()
router.register(
    r"pickup_locations", views.PickupLocationViewSet, basename="pickup_locations"
)
router.register(
    r"public_pickup_locations",
    views.PublicPickupLocationViewSet,
    basename="public_pickup_locations",
)
urlpatterns += router.urls
