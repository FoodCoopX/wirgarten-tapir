from django.urls import path

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
        "csv_export_list",
        views.GetCsvExportsView.as_view(),
        name="csv_export_list",
    ),
]
