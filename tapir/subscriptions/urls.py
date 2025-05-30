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
        "api/cancelled_subscriptions",
        views.CancelledSubscriptionsApiView.as_view(),
        name="cancelled_subscriptions",
    ),
    path(
        "api/confirm_subscription_changes",
        views.ConfirmSubscriptionChangesView.as_view(),
        name="confirm_subscription_changes",
    ),
    path(
        "api/product_types_and_number_of_cancelled_subscriptions",
        views.ProductTypesAndNumberOfCancelledSubscriptionsToConfirmView.as_view(),
        name="product_types_and_number_of_cancelled_subscriptions",
    ),
    path(
        "api/member_data_to_confirm",
        views.MemberDataToConfirmApiView.as_view(),
        name="member_data_to_confirm",
    ),
]

router = DefaultRouter()
router.register(
    r"products",
    views.ProductViewSet,
    basename="products",
)
urlpatterns += router.urls
