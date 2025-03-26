from django.urls import path
from rest_framework.routers import DefaultRouter

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
    path(
        "api/extended_product",
        views.ExtendedProductView.as_view(),
        name="extended_product",
    ),
]

router = DefaultRouter()
urlpatterns += router.urls
