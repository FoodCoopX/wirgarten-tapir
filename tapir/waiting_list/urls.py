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
]

router = DefaultRouter()
router.register(
    r"waiting_list_entries",
    views.WaitingListEntryViewSet,
    basename="waiting_list_entries",
)
urlpatterns += router.urls
