from django.urls import path

from tapir.deliveries import views

app_name = "Deliveries"
urlpatterns = [
    path(
        "api/member_joker_information",
        views.GetMemberJokerInformationView.as_view(),
        name="member_joker_information",
    ),
    path(
        "api/member_deliveries",
        views.GetMemberDeliveriesView.as_view(),
        name="member_deliveries",
    ),
    path(
        "api/cancel_joker",
        views.CancelJokerView.as_view(),
        name="cancel_joker",
    ),
    path(
        "api/use_joker",
        views.UseJokerView.as_view(),
        name="use_joker",
    ),
]
