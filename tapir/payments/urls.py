from django.urls import path

from tapir.payments import views

app_name = "payments"
urlpatterns = [
    path(
        "api/member_future_payments",
        views.GetFutureMemberPaymentsApiView.as_view(),
        name="member_future_payments",
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
]
