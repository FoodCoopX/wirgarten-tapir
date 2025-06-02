from django.urls import path

from tapir.core import views

app_name = "core"
urlpatterns = [
    path(
        "api/get_theme",
        views.GetThemeView.as_view(),
        name="get_theme",
    ),
]
