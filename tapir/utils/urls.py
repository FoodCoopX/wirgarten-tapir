from django.urls import path

from tapir.utils import views

app_name = "utils"
urlpatterns = [
    path(
        "reset_test_data",
        views.ResetTestData.as_view(),
        name="reset_test_data",
    ),
]
