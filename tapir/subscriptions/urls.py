from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.subscriptions.views import admin_subscription_changes
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
        "api/member_subscription_data",
        member_profile.GetMemberSubscriptionDataApiView.as_view(),
        name="member_subscription_data",
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
    path(
        "api/dates_change",
        other.SubscriptionDateChangeApiView.as_view(),
        name="dates_change",
    ),
    path(
        "api/convert_week_to_date_for_subscription_change",
        other.ConvertWeekToDateForSubscriptionChangeApiView.as_view(),
        name="convert_week_to_date_for_subscription_change",
    ),
    path(
        "api/subscription_price_override",
        other.SubscriptionPriceOverrideApiView.as_view(),
        name="subscription_price_override",
    ),
    path(
        "api/subscription_trial_change",
        other.SubscriptionTrialChangeApiView.as_view(),
        name="subscription_trial_change",
    ),
    path(
        "api/admin_subscription_change_member_search",
        admin_subscription_changes.AdminSubscriptionChangeMemberSearchApiView.as_view(),
        name="admin_subscription_change_member_search",
    ),
    path(
        "api/admin_subscription_change_member_data",
        admin_subscription_changes.AdminSubscriptionChangeMemberDataApiView.as_view(),
        name="admin_subscription_change_member_data",
    ),
    path(
        "api/admin_size_change_date_options",
        admin_subscription_changes.AdminSizeChangeDateOptionsApiView.as_view(),
        name="admin_size_change_date_options",
    ),
    path(
        "api/admin_size_change_check",
        admin_subscription_changes.AdminSizeChangeCheckApiView.as_view(),
        name="admin_size_change_check",
    ),
    path(
        "api/admin_size_change_apply",
        admin_subscription_changes.AdminSizeChangeApplyApiView.as_view(),
        name="admin_size_change_apply",
    ),
    path(
        "api/admin_subscription_addition_date_options",
        admin_subscription_changes.AdminSubscriptionAdditionDateOptionsApiView.as_view(),
        name="admin_subscription_addition_date_options",
    ),
    path(
        "api/admin_subscription_addition_check",
        admin_subscription_changes.AdminSubscriptionAdditionCheckApiView.as_view(),
        name="admin_subscription_addition_check",
    ),
    path(
        "api/admin_subscription_addition_apply",
        admin_subscription_changes.AdminSubscriptionAdditionApplyApiView.as_view(),
        name="admin_subscription_addition_apply",
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
router.register(
    r"subscriptions",
    other.SubscriptionViewSet,
    basename="subscriptions",
)
urlpatterns += router.urls
