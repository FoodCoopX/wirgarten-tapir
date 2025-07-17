from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.waiting_list import views

app_name = "waiting_list"
urlpatterns = [
    path(
        "list",
        views.WaitingListView.as_view(),
        name="list",
    ),
    path(
        "api/list",
        views.WaitingListApiView.as_view(),
        name="api_list",
    ),
    path(
        "api/update_entry",
        views.WaitingListEntryUpdateView.as_view(),
        name="update_entry",
    ),
    path(
        "api/categories",
        views.WaitingListCategoriesView.as_view(),
        name="categories",
    ),
    path(
        "api/show_coop_content",
        views.WaitingListShowsCoopContentView.as_view(),
        name="show_coop_content",
    ),
    path(
        "api/public_waiting_list_create_entry_new_member",
        views.PublicWaitingListCreateEntryNewMemberView.as_view(),
        name="public_waiting_list_create_entry_new_member",
    ),
    path(
        "api/waiting_list_create_entry_existing_member",
        views.WaitingListCreateEntryExistingMemberView.as_view(),
        name="waiting_list_create_entry_existing_member",
    ),
    path(
        "api/send_waiting_list_link",
        views.SendWaitingListLinkApiView.as_view(),
        name="send_waiting_list_link",
    ),
    path(
        "api/disable_waiting_list_link",
        views.DisableWaitingListLinkApiView.as_view(),
        name="disable_waiting_list_link",
    ),
    path(
        "waiting_list_confirm",
        views.WaitingListConfirmOrderView.as_view(),
        name="waiting_list_confirm",
    ),
    path(
        "api/public_get_waiting_list_entry_details",
        views.PublicGetWaitingListEntryDetailsApiView.as_view(),
        name="public_get_waiting_list_entry_details",
    ),
    path(
        "api/public_confirm_waiting_list_entry",
        views.PublicConfirmWaitingListEntryView.as_view(),
        name="public_confirm_waiting_list_entry",
    ),
    path("api/counts", views.WaitingListGetCountsApiView.as_view(), name="counts"),
]

router = DefaultRouter()
router.register(
    r"waiting_list_entries",
    views.WaitingListEntryViewSet,
    basename="waiting_list_entries",
)
urlpatterns += router.urls
