from django.urls import path

from tapir.wirgarten.views import (
    RegistrationWizardView,
    RegistrationWizardConfirmView,
    exported_files,
)

app_name = "wirgarten"
urlpatterns = [
    path(
        "register",
        RegistrationWizardView.as_view(),
        name="draftuser_register",
    ),
    path(
        "register/confirm",
        RegistrationWizardConfirmView.as_view(),
        name="draftuser_confirm_registration",
    ),
    path(
        "admin/exportedfiles",
        exported_files.ExportedFilesListView.as_view(),
        name="exported_files_list",
    ),
    path(
        "admin/exportedfiles/<int:pk>/download",
        exported_files.download,
        name="exported_files_download",
    ),
]
