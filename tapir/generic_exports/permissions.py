from rest_framework import permissions

from tapir.wirgarten.constants import Permission


class HasCoopManagePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm(Permission.Coop.MANAGE)


class IsReadOnly(permissions.BasePermission):
    """
    Allows safe methods only. Compose it to let everyone read what only some
    may change, e.g. `[IsAuthenticated, IsReadOnly | HasCoopManagePermission]`.

    DRF's own IsAuthenticatedOrReadOnly splits on anonymous-vs-authenticated,
    and DjangoModelPermissions expects Django model permissions while
    TapirUser.has_perm resolves Keycloak roles, so neither fits here.
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
