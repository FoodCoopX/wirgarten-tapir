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
        "api/public_waiting_list_create_entry_existing_member",
        views.PublicWaitingListCreateEntryExistingMemberView.as_view(),
        name="public_waiting_list_create_entry_existing_member",
    ),
]

router = DefaultRouter()
router.register(
    r"waiting_list_entries",
    views.WaitingListEntryViewSet,
    basename="waiting_list_entries",
)
urlpatterns += router.urls
