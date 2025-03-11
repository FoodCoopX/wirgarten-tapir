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
]

router = DefaultRouter()
router.register(r"csv_exports", views.CsvExportViewSet, basename="csv_exports")
urlpatterns += router.urls
