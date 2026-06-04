from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.payments import views

app_name = "payments"
urlpatterns = [
    path(
        "api/member_future_payments",
        views.GetFutureMemberPaymentsApiView.as_view(),
        name="member_future_payments",
    ),
    path(
        "api/member_past_payments",
        views.GetPastMemberPaymentsApiView.as_view(),
        name="member_past_payments",
    ),
    path(
        "api/member_payment_rhythm_data",
        views.GetMemberPaymentRhythmDataApiView.as_view(),
        name="member_payment_rhythm_data",
    ),
    path(
        "api/set_member_payment_rhythm",
        views.SetMemberPaymentRhythmApiView.as_view(),
        name="set_member_payment_rhythm",
    ),
    path("credit_list", views.MemberCreditTemplateView.as_view(), name="credit_list"),
    path(
        "api/credit_list_filtered",
        views.MemberCreditListApiView.as_view(),
        name="credit_list_filtered",
    ),
    path(
        "api/member_credit_create",
        views.MemberCreditCreateApiView.as_view(),
        name="member_credit_create",
    ),
    path(
        "api/member_credit_settle",
        views.MemberCreditSettleApiView.as_view(),
        name="member_credit_settle",
    ),
    path(
        "api/can_logged_in_user_change_targets_payment_rhythm",
        views.CabLoggedInUserChangeTargetsPaymentRhythm.as_view(),
        name="can_logged_in_user_change_targets_payment_rhythm",
    ),
    path(
        "api/mandate_reference_preview",
        views.MandateReferencePreviewApiView.as_view(),
        name="mandate_reference_preview",
    ),
    path(
        "api/intended_use_preview_contracts",
        views.PaymentIntendedUsePreviewContractsApiView.as_view(),
        name="intended_use_preview_contracts",
    ),
    path(
        "api/intended_use_preview_coop_shares",
        views.PaymentIntendedUsePreviewCoopSharesApiView.as_view(),
        name="intended_use_preview_coop_shares",
    ),
    path(
        "payment_transaction_list",
        views.PaymentTransactionsListView.as_view(),
        name="payment_transaction_list",
    ),
    path(
        "payment_transaction_details",
        views.PaymentTransactionDetailsView.as_view(),
        name="payment_transaction_details",
    ),
]

router = DefaultRouter()
router.register(
    r"payment_transactions",
    views.PaymentTransactionViewSet,
    basename="payment_transactions",
)
urlpatterns += router.urls
