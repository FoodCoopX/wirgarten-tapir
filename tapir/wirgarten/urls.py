from django.urls import path

from tapir.wirgarten.views import (
    RegistrationWizardView,
    RegistrationWizardConfirmView,
    exported_files,
)
from tapir.wirgarten.views.member import (
    MemberListView,
    MemberDetailView,
    MemberPaymentsView,
    MemberDeliveriesView,
    get_payment_amount_edit_form,
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
        "admin/exportedfiles/<str:pk>/download",
        exported_files.download,
        name="exported_files_download",
    ),
    path("members", MemberListView.as_view(), name="member_list"),
    path("members/<int:pk>", MemberDetailView.as_view(), name="member_detail"),
    path("payments/<int:pk>", MemberPaymentsView.as_view(), name="member_payments"),
    path(
        "payments/<int:member_id>/edit/<str:mandate_ref_id>/<str:payment_due_date>",
        get_payment_amount_edit_form,
        name="member_payments_edit",
    ),
    path(
        "deliveries/<int:pk>", MemberDeliveriesView.as_view(), name="member_deliveries"
    ),
]
