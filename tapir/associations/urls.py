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
