from django.urls import path
from rest_framework.routers import DefaultRouter

from tapir.associations import views

app_name = "associations"
urlpatterns = [
    path(
        "association_memberships_config",
        views.AssociationMembershipConfigView.as_view(),
        name="association_memberships_config",
    ),
    path(
        "api/member_association_memberships",
        views.MemberAssociationMembershipDetails.as_view(),
        name="member_association_memberships",
    ),
    path(
        "api/admin_create_membership",
        views.AdminSetAssociationMembership.as_view(),
        name="admin_create_membership",
    ),
    path(
        "api/existing_member_updates_membership",
        views.ExistingMemberUpdatesAssociationMembershipApiView.as_view(),
        name="existing_member_updates_membership",
    ),
    path(
        "api/set_membership_end_date",
        views.SetAssociationMembershipEndDateApiView.as_view(),
        name="set_membership_end_date",
    ),
    path(
        "api/number_of_association_members_per_month",
        views.NumberOfAssociationMembersPerMonthApiView.as_view(),
        name="number_of_association_members_per_month",
    ),
    path(
        "api/number_of_association_membership_cancellations_per_month",
        views.NumberOfAssociationMembershipCancellationRelativeToEndDatePerMonthApiView.as_view(),
        name="number_of_association_membership_cancellations_per_month",
    ),
    path(
        "api/number_of_association_membership_cancellations_per_month_relative_to_cancellation",
        views.NumberOfAssociationMembershipCancellationRelativeToCancellationDatePerMonthApiView.as_view(),
        name="number_of_association_membership_cancellations_per_month_relative_to_cancellation",
    ),
]

router = DefaultRouter()
router.register(
    r"association_membership_types",
    views.AssociationMembershipTypeViewSet,
    basename="association_membership_types",
)
router.register(
    r"association_membership_types_price",
    views.AssociationMembershipTypePriceViewSet,
    basename="association_membership_types_price",
)
urlpatterns += router.urls
