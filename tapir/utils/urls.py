from django.conf import settings
from django.urls import path

from tapir.utils import views

app_name = "utils"
urlpatterns = [
    path("data_import", views.DataImportView.as_view(), name="data_import"),
    path(
        "data_import/apply",
        views.DataImportApplyView.as_view(),
        name="data_import_apply",
    ),
    path(
        "data_import/activation",
        views.DataImportActivationView.as_view(),
        name="data_import_activation",
    ),
    path(
        "data_import/template/<str:import_type>",
        views.DataImportTemplateView.as_view(),
        name="data_import_template",
    ),
]
if settings.DEBUG:
    urlpatterns += [
        path(
            "reset_test_data",
            views.ResetTestData.as_view(),
            name="reset_test_data",
        ),
    ]
