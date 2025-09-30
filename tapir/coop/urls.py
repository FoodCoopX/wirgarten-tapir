from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.coop import views

app_name = "coop"
urlpatterns = [
    path(
        "api/delete_member",
        views.DeleteMemberApiView.as_view(),
        name="delete_member",
    ),
    path(
        "api/get_member_details",
        views.GetMemberDetailsApiView.as_view(),
        name="get_member_details",
    ),
]
