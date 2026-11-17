from rest_framework import permissions

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class IsPaymentExportExclusionEnabled(permissions.BasePermission):
    def has_permission(self, request, view):
        return get_parameter_value(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, cache=view.cache
        )
