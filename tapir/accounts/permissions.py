from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from tapir.wirgarten.constants import Permission


class HasAccountsManagePermission(permissions.BasePermission):
    def has_permission(self, request: Request, view: APIView):
        return request.user.has_perm(Permission.Accounts.MANAGE)
