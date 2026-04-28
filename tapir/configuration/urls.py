from django.urls import path

from tapir.configuration import views

app_name = "configuration"
urlpatterns = [
    path(
        "parameters",
        views.ParameterView.as_view(),
        name="parameters",
    ),
    path(
        "member-number-preview",
        views.MemberNumberPreviewView.as_view(),
        name="member_number_preview",
    ),
]
