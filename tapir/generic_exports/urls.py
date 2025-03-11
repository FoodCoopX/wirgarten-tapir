from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.generic_exports import views

app_name = "generic_exports"
urlpatterns = [
    path(
        "csv_export_editor",
        views.CsvExportEditorView.as_view(),
        name="csv_export_editor",
    ),
    path(
        "export_segments",
        views.GetExportSegmentsView.as_view(),
        name="export_segments",
    ),
    path(
        "build_csv_export",
        views.BuildCsvExportView.as_view(),
        name="build_csv_export",
    ),
]

router = DefaultRouter()
router.register(r"csv_exports", views.CsvExportViewSet, basename="csv_exports")
urlpatterns += router.urls
