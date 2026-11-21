from django.conf import settings
from django.urls import path

from tapir.utils import views
from tapir.utils import views_data_import_api as data_import_api

app_name = "utils"
urlpatterns = [
    path("data_import", views.DataImportView.as_view(), name="data_import"),
    path(
        "data_import/types",
        data_import_api.DataImportTypesApi.as_view(),
        name="data_import_types",
    ),
    path(
        "data_import/upload",
        data_import_api.DataImportUploadApi.as_view(),
        name="data_import_upload",
    ),
    path(
        "data_import/mapping",
        data_import_api.DataImportMappingApi.as_view(),
        name="data_import_mapping",
    ),
    path(
        "data_import/cell",
        data_import_api.DataImportCellEditApi.as_view(),
        name="data_import_cell",
    ),
    path(
        "data_import/apply",
        data_import_api.DataImportApplyApi.as_view(),
        name="data_import_apply",
    ),
    path(
        "data_import/activation",
        data_import_api.DataImportActivationApi.as_view(),
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
        path("reset_test_data", views.ResetTestData.as_view(), name="reset_test_data")
    ]
