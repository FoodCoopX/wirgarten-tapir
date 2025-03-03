from django.urls import path

from tapir.jokers import views

app_name = "Jokers"
urlpatterns = [
    path(
        "api/member_jokers",
        views.GetMemberJokers.as_view(),
        name="member_jokers",
    ),
]
