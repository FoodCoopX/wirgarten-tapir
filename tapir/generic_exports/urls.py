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
    path(
        "pdf_export_editor",
        views.PdfExportEditorView.as_view(),
        name="pdf_export_editor",
    ),
]

router = DefaultRouter()
router.register(r"csv_exports", views.CsvExportViewSet, basename="csv_exports")
router.register(r"pdf_exports", views.PdfExportViewSet, basename="pdf_exports")
urlpatterns += router.urls
