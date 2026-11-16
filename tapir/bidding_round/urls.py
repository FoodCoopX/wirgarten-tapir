from django.urls import path

from tapir.bidding_round import views

app_name = "bidding_rounds"

urlpatterns = [
    path("", views.BiddingRoundView.as_view(), name="bidding_rounds"),
    path("admin", views.BiddingRoundConfigView.as_view(), name="bidding_rounds_config"),
    path(
        "admin/<str:round_id>/results",
        views.BiddingRoundResultsView.as_view(),
        name="bidding_rounds_results",
    ),
    path("api/public_data", views.PublicDataView.as_view(), name="public_data"),
    path("api", views.RoundListCreateView.as_view(), name="round_list_create"),
    path(
        "api/growing_periods",
        views.GrowingPeriodsView.as_view(),
        name="growing_periods",
    ),
    path(
        "api/available_product_types",
        views.AvailableProductTypesView.as_view(),
        name="available_product_types",
    ),
    path(
        "api/<str:round_id>",
        views.RoundDetailView.as_view(),
        name="round_detail",
    ),
    path(
        "api/<str:round_id>/start",
        views.RoundStartView.as_view(),
        name="round_start",
    ),
    path(
        "api/<str:round_id>/close",
        views.RoundCloseView.as_view(),
        name="round_close",
    ),
    path(
        "api/<str:round_id>/reopen",
        views.RoundReopenView.as_view(),
        name="round_reopen",
    ),
    path(
        "api/<str:round_id>/public_results",
        views.PublicResultsView.as_view(),
        name="public_results",
    ),
    path(
        "api/<str:round_id>/results",
        views.RoundResultsView.as_view(),
        name="round_results",
    ),
    path(
        "api/<str:round_id>/bid",
        views.MemberBidView.as_view(),
        name="member_bid",
    ),
    path(
        "api/<str:round_id>/create_contracts",
        views.CreateContractsView.as_view(),
        name="create_contracts",
    ),
]
