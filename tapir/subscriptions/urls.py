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
    path(
        "api/confirm_subscription_changes",
        views.ConfirmSubscriptionChangesView.as_view(),
        name="confirm_subscription_changes",
    ),
    path(
        "api/member_data_to_confirm",
        views.MemberDataToConfirmApiView.as_view(),
        name="member_data_to_confirm",
    ),
    path(
        "bestell_wizard",
        views.BestellWizardView.as_view(),
        name="bestell_wizard",
    ),
]

router = DefaultRouter()
router.register(
    r"products",
    views.ProductViewSet,
    basename="products",
)
urlpatterns += router.urls
