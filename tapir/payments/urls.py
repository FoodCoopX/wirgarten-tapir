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
        views.GetMemberPaymentRhythmData.as_view(),
        name="member_payment_rhythm_data",
    ),
]
