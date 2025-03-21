from django.urls import path

from tapir.subscriptions import views

app_name = "subscriptions"
urlpatterns = [
    path(
        "cancellation_data",
        views.GetCancellationDataView.as_view(),
        name="cancellation_data",
    ),
    path(
        "cancel_subscriptions",
        views.CancelSubscriptionsView.as_view(),
        name="cancel_subscriptions",
    ),
]
