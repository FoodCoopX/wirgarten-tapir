from django.urls import path

from tapir.wirgarten.views import (
    RegistrationWizardView,
    RegistrationWizardConfirmView,
    exported_files,
)
from tapir.wirgarten.views.form_period import (
    get_period_add_form,
    get_period_copy_form,
    delete_period,
)
from tapir.wirgarten.views.form_product_type import (
    get_product_type_edit_form,
    get_product_type_add_form,
    delete_product_type,
)
from tapir.wirgarten.views.form_product import (
    get_product_edit_form,
    get_product_add_form,
    delete_product,
)
from tapir.wirgarten.views.member import (
    MemberListView,
    MemberDetailView,
    MemberPaymentsView,
    MemberDeliveriesView,
    get_payment_amount_edit_form,
)
from tapir.wirgarten.views.product_cfg import ProductCfgView
from tapir.wirgarten.views.payments import PaymentTransactionListView

app_name = "wirgarten"


urlpatterns = [
    path(
        "product",
        ProductCfgView.as_view(),
        name="product",
    ),
    path(
        "product/<str:prodTypeId>/<str:periodId>/typeedit",
        get_product_type_edit_form,
        name="product_type_edit",
    ),
    path(
        "product/<str:periodId>/typeadd",
        get_product_type_add_form,
        name="product_type_add",
    ),
    path(
        "product/<str:prodTypeId>/<str:periodId>/typedelete",
        delete_product_type,
        name="product_type_delete",
    ),
    path("product/<str:prodId>/edit", get_product_edit_form, name="product_edit"),
    path("product/<str:prodTypeId>/add", get_product_add_form, name="product_add"),
    path("product/<str:prodId>/delete", delete_product, name="product_delete"),
    path("product/periodadd", get_period_add_form, name="period_add"),
    path("product/<str:periodId>/periodcopy", get_period_copy_form, name="period_copy"),
    path("product/<str:periodId>/perioddelete", delete_period, name="period_delete"),
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
    path("sepa", PaymentTransactionListView.as_view(), name="payment_transactions"),
]
