from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.subscriptions.views import cancellations
from tapir.subscriptions.views import confirmations
from tapir.subscriptions.views import member_profile
from tapir.subscriptions.views import other

app_name = "subscriptions"
urlpatterns = [
    path(
        "cancellation_data",
        cancellations.GetCancellationDataView.as_view(),
        name="cancellation_data",
    ),
    path(
        "cancel_subscriptions",
        cancellations.CancelSubscriptionsView.as_view(),
        name="cancel_subscriptions",
    ),
    path(
        "api/extended_product",
        other.ExtendedProductView.as_view(),
        name="extended_product",
    ),
    path(
        "api/confirm_subscription_changes",
        confirmations.ConfirmSubscriptionChangesView.as_view(),
        name="confirm_subscription_changes",
    ),
    path(
        "api/member_data_to_confirm",
        confirmations.MemberDataToConfirmApiView.as_view(),
        name="member_data_to_confirm",
    ),
    path(
        "api/member_subscriptions",
        member_profile.GetMemberSubscriptionsApiView.as_view(),
        name="member_subscriptions",
    ),
    path(
        "api/update_subscription",
        member_profile.UpdateSubscriptionsApiView.as_view(),
        name="update_subscription",
    ),
    path(
        "api/member_profile_capacity_check",
        member_profile.MemberProfileCapacityCheckApiView.as_view(),
        name="member_profile_capacity_check",
    ),
    path(
        "api/revoke_changes",
        confirmations.RevokeChangesApiView.as_view(),
        name="revoke_changes",
    ),
]

router = DefaultRouter()
router.register(
    r"products",
    other.ProductViewSet,
    basename="products",
)
router.register(
    r"public_product_types",
    other.PublicProductTypeViewSet,
    basename="public_product_types",
)
urlpatterns += router.urls
