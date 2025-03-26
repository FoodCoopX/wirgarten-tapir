from django.urls import path

from tapir.pickup_locations import views

app_name = "pickup_locations"
urlpatterns = [
    path(
        "api/pickup_location_capacities",
        views.PickupLocationCapacitiesView.as_view(),
        name="pickup_location_capacities",
    ),
]
