from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import authentication


class DrfForwardAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request._request.user.is_authenticated:
            return (request._request.user, None)
        return None


class DrfForwardAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "tapir.accounts.drf_authentication.DrfForwardAuthentication"  # full import path OR class ref
    name = "DrfForwardAuthentication"  # name used in the schema

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "basic",
        }
