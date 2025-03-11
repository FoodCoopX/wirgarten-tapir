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
    path(
        "create_csv_export",
        views.CreateCsvExportView.as_view(),
        name="create_csv_export",
    ),
]
