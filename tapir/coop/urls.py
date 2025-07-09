from django.urls import path

from tapir.coop import views

app_name = "coop"
urlpatterns = [
    path(
        "api/minimum_number_of_shares",
        views.MinimumNumberOfSharesApiView.as_view(),
        name="minimum_number_of_shares",
    ),
]
