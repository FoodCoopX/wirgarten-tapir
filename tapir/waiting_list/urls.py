from django.urls import path

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
]
