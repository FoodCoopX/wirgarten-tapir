from icecream import ic
from rest_framework import permissions

from tapir.wirgarten.constants import Permission


class HasCoopManagePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        ic("has_permission", request.user.has_perm(Permission.Coop.MANAGE))
        return request.user.has_perm(Permission.Coop.MANAGE)
