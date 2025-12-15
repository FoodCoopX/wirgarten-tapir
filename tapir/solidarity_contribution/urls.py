from django.urls import path

from tapir.solidarity_contribution.views import (
    MemberSolidarityContributionsApiView,
    UpdateMemberSolidarityContributionApiView,
)

app_name = "solidarity_contribution"
urlpatterns = [
    path(
        "api/member_solidarity_contributions",
        MemberSolidarityContributionsApiView.as_view(),
        name="member_solidarity_contributions",
    ),
    path(
        "api/update_member_contribution",
        UpdateMemberSolidarityContributionApiView.as_view(),
        name="update_member_contribution",
    ),
]
