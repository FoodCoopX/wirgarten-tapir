from django.urls import path

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
]
