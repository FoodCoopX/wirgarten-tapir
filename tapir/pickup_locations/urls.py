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
]

router = DefaultRouter()
router.register(
    r"pickup_locations", views.PickupLocationViewSet, basename="pickup_locations"
)
urlpatterns += router.urls
