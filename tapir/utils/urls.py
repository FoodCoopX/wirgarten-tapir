from django.conf import settings
from django.urls import path

app_name = "utils"
if settings.DEBUG:
    from tapir.utils import views

    urlpatterns = [
        path(
            "reset_test_data",
            views.ResetTestData.as_view(),
            name="reset_test_data",
        ),
    ]
else:
    urlpatterns = []
