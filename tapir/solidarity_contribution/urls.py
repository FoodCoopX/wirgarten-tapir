from django.urls import path

from tapir.solidarity_contribution.views import MemberSolidarityContributionsApiView

app_name = "solidarity_contribution"
urlpatterns = [
    path(
        "api/member_solidarity_contributions",
        MemberSolidarityContributionsApiView.as_view(),
        name="member_solidarity_contributions",
    ),
]
