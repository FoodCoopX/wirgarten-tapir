from django.urls import path

from tapir.deliveries import views

app_name = "Jokers"
urlpatterns = [
    path(
        "api/member_jokers",
        views.GetMemberJokersView.as_view(),
        name="member_jokers",
    ),
    path(
        "api/member_deliveries",
        views.GetMemberDeliveriesView.as_view(),
        name="member_deliveries",
    ),
]
