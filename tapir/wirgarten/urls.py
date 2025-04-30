from django.urls import path

from tapir.wirgarten.views import exported_files
from tapir.wirgarten.views.contracts import (
    ExportSubscriptionList,
    NewContractsView,
    SubscriptionListView,
    confirm_new_contracts,
    NewSubscriptionCancellationsView,
)
from tapir.wirgarten.views.debug.scheduled_tasks import (
    JobsListView,
    ScheduledTasksListView,
    run_job,
)
from tapir.wirgarten.views.default_redirect import dynamic_view
from tapir.wirgarten.views.member.details.actions import (
    cancel_contract_at_period_end,
    renew_contract_same_conditions,
)
from tapir.wirgarten.views.member.details.member_details import MemberDetailView
from tapir.wirgarten.views.member.details.modals import (
    get_add_coop_shares_form,
    get_add_subscription_form,
    get_cancel_trial_form,
    get_cancellation_reason_form,
    get_coop_shares_waiting_list_form,
    get_harvest_shares_waiting_list_form,
    get_member_payment_data_edit_form,
    get_member_personal_data_edit_form,
    get_pickup_location_choice_form,
    get_renew_contracts_form,
)
from tapir.wirgarten.views.member.list.actions import (
    ExportMembersView,
    export_coop_member_list,
    resend_verify_email,
)
from tapir.wirgarten.views.member.list.member_deliveries import MemberDeliveriesView
from tapir.wirgarten.views.member.list.member_list import MemberListView
from tapir.wirgarten.views.member.list.member_payments import (
    MemberPaymentsView,
    get_payment_amount_edit_form,
)
from tapir.wirgarten.views.member.list.modals import (
    get_cancel_non_trial_form,
    get_coop_share_cancel_form,
    get_coop_share_transfer_form,
    get_edit_price_form,
    get_member_personal_data_create_form,
    get_edit_dates_form,
)
from tapir.wirgarten.views.payments import PaymentTransactionListView
from tapir.wirgarten.views.pickup_location_config import (
    PickupLocationCfgView,
    delete_pickup_location,
    get_pickup_location_add_form,
    get_pickup_location_edit_form,
)
from tapir.wirgarten.views.product_cfg import (
    ProductCfgView,
    delete_period,
    delete_product_handler,
    delete_product_type,
    get_period_add_form,
    get_period_copy_form,
    get_product_add_form,
    get_product_edit_form,
    get_product_type_capacity_add_form,
    get_product_type_capacity_edit_form,
)
from tapir.wirgarten.views.register import (
    RegistrationWizardConfirmView,
    questionaire_trafficsource_view,
)
from tapir.wirgarten.views.waitlist import WaitingListView, export_waitinglist

urlpatterns = [
    path(
        "product",
        ProductCfgView.as_view(),
        name="product",
    ),
    path(
        "product/<str:periodId>/<str:capacityId>/typeedit",
        get_product_type_capacity_edit_form,
        name="product_type_edit",
    ),
    path(
        "product/<str:periodId>/typeadd",
        get_product_type_capacity_add_form,
        name="product_type_add",
    ),
    path(
        "product/<str:periodId>/<str:capacityId>/typedelete",
        delete_product_type,
        name="product_type_delete",
    ),
    path(
        "product/<str:periodId>/<str:capacityId>/add",
        get_product_add_form,
        name="product_add",
    ),
    path(
        "product/<str:periodId>/<str:capacityId>/<str:prodId>/edit",
        get_product_edit_form,
        name="product_edit",
    ),
    path(
        "product/<str:periodId>/<str:capacityId>/<str:prodId>/delete",
        delete_product_handler,
        name="product_delete",
    ),
    path("product/periodadd", get_period_add_form, name="period_add"),
    path("product/<str:periodId>/periodcopy", get_period_copy_form, name="period_copy"),
    path("product/<str:periodId>/perioddelete", delete_period, name="period_delete"),
    path(
        "register",
        dynamic_view("draftuser_register"),
        name="draftuser_register",
    ),
    path(
        "register/confirm",
        RegistrationWizardConfirmView.as_view(),
        name="draftuser_confirm_registration",
    ),
    path(
        "admin/dashboard",
        dynamic_view("admin_dashboard"),
        name="admin_dashboard",
    ),
    path(
        "admin/dashboard/data/cashflow",
        dynamic_view("admin_dashboard_cashflow_data"),
        name="admin_dashboard_cashflow_data",
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
    path(
        "admin/pickuplocations",
        PickupLocationCfgView.as_view(),
        name="pickup_locations",
    ),
    path(
        "admin/pickuplocations/add",
        get_pickup_location_add_form,
        name="pickup_locations_add",
    ),
    path(
        "admin/pickuplocations/edit/<str:id>",
        get_pickup_location_edit_form,
        name="pickup_locations_edit",
    ),
    path(
        "admin/pickuplocations/delete/<str:id>",
        delete_pickup_location,
        name="pickup_locations_delete",
    ),
    path(
        "admin/waitinglist",
        WaitingListView.as_view(),
        name="waitinglist",
    ),
    path("admin/waitinglist/export", export_waitinglist, name="export_waitlist"),
    path("admin/newcontracts", NewContractsView.as_view(), name="new_contracts"),
    path(
        "admin/new_contract_cancellations",
        NewSubscriptionCancellationsView.as_view(),
        name="new_contract_cancellations",
    ),
    path(
        "admin/newcontracts/confirm",
        confirm_new_contracts,
        name="new_contracts_confirm",
    ),
    path(
        "register/waitlist/hs",
        get_harvest_shares_waiting_list_form,
        name="waitlist_harvestshares",
    ),
    path(
        "register/waitlist/cs",
        get_coop_shares_waiting_list_form,
        name="waitlist_coopshares",
    ),
    path("members", MemberListView.as_view(), name="member_list"),
    path("members/create", get_member_personal_data_create_form, name="member_create"),
    path(
        "members/<str:pk>/edit", get_member_personal_data_edit_form, name="member_edit"
    ),
    path(
        "members/<str:pk>/editpaymentdetails",
        get_member_payment_data_edit_form,
        name="member_edit_payment_details",
    ),
    path(
        "members/<str:pk>/editpickuplocation",
        get_pickup_location_choice_form,
        name="member_pickup_location_choice",
    ),
    path(
        "members/<str:pk>/cancelcontract",
        cancel_contract_at_period_end,
        name="member_cancel_contract",
    ),
    path(
        "members/<str:pk>/renewcontract",
        renew_contract_same_conditions,
        name="member_renew_same_conditions",
    ),
    path(
        "members/<str:pk>/renewcontractwithchanges",
        get_renew_contracts_form,
        name="member_renew_changed_conditions",
    ),
    path(
        "members/<str:pk>/addsubscription",
        get_add_subscription_form,
        name="member_add_subscription",
    ),
    path(
        "members/<str:pk>/addcoopshares",
        get_add_coop_shares_form,
        name="member_add_coop_shares",
    ),
    path(
        "members/<str:pk>/canceltrial",
        get_cancel_trial_form,
        name="member_cancel_trial",
    ),
    path(
        "members/<str:pk>/cancelnontrial",
        get_cancel_non_trial_form,
        name="member_cancel_non_trial",
    ),
    path(
        "members/<str:pk>/resendverifyemail",
        resend_verify_email,
        name="member_resend_verify_email",
    ),
    path(
        "members/exportoverview",
        ExportMembersView.as_view(),
        name="member_overview_export",
    ),
    path(
        "members/exportcoopmemberlist",
        export_coop_member_list,
        name="member_list_coop_export",
    ),
    path("members/<str:pk>", MemberDetailView.as_view(), name="member_detail"),
    path(
        "members/<str:pk>/coopsharestransfer",
        get_coop_share_transfer_form,
        name="member_coopshare_transfer",
    ),
    path(
        "members/<str:pk>/coopsharescancel",
        get_coop_share_cancel_form,
        name="member_coopshare_cancel",
    ),
    path("contracts", SubscriptionListView.as_view(), name="subscription_list"),
    path(
        "contracts/exportoverview",
        ExportSubscriptionList.as_view(),
        name="subscription_overview_export",
    ),
    path(
        "contracts/<str:pk>/editprice",
        get_edit_price_form,
        name="subscription_edit_price",
    ),
    path(
        "contracts/<str:pk>/editdates",
        get_edit_dates_form,
        name="subscription_edit_dates",
    ),
    path("payments/<str:pk>", MemberPaymentsView.as_view(), name="member_payments"),
    path(
        "payments/<str:member_id>/edit/<str:mandate_ref_id>/<str:payment_due_date>",
        get_payment_amount_edit_form,
        name="member_payments_edit",
    ),
    path("sepa", PaymentTransactionListView.as_view(), name="payment_transactions"),
    path(
        "deliveries/<str:pk>", MemberDeliveriesView.as_view(), name="member_deliveries"
    ),
    path(
        "registration/marketingfeedback",
        questionaire_trafficsource_view,
        name="marketing_feedback_form",
    ),
    path(
        "member/<str:pk>/cancellation_reason",
        get_cancellation_reason_form,
        name="cancellation_reason",
    ),
    path("admin/debug/tasks", ScheduledTasksListView.as_view(), name="scheduled_tasks"),
    path("admin/debug/jobs", JobsListView.as_view(), name="jobs"),
    path("admin/debug/jobs/execute", run_job, name="job_execute"),
]
app_name = "wirgarten"
