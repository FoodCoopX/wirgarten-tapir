from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.coop import views

app_name = "coop"
urlpatterns = [
    path(
        "api/minimum_number_of_shares",
        views.MinimumNumberOfSharesApiView.as_view(),
        name="minimum_number_of_shares",
    ),
    path(
        "api/existing_member_purchases_shares",
        views.ExistingMemberPurchasesSharesApiView.as_view(),
        name="existing_member_purchases_shares",
    ),
    path(
        "api/get_coop_share_transactions",
        views.GetCoopShareTransactionsApiView.as_view(),
        name="get_coop_share_transactions",
    ),
    path(
        "api/delete_member",
        views.DeleteMemberApiView.as_view(),
        name="delete_member",
    ),
    path(
        "api/member_banking_data",
        views.MemberBankDataApiView.as_view(),
        name="member_banking_data",
    ),
    path(
        "api/member_personal_data",
        views.MemberPersonalDataApiView.as_view(),
        name="member_personal_data",
    ),
]

router = DefaultRouter()
router.register(
    r"members",
    views.MemberViewSet,
    basename="members",
)
urlpatterns += router.urls
