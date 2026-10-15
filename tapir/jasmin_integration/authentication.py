import apps.authz.openapi  # noqa: F401 registers the schema of Jasmin's JWT authentication
from drf_spectacular.authentication import SessionScheme
from rest_framework.authentication import SessionAuthentication

from tapir.accounts.drf_authentication import (
    DrfForwardAuthentication,
    DrfForwardAuthenticationScheme,
)

# Jasmin's API is mounted where its frontend expects it, see tapir.urls.
JASMIN_API_PATH_PREFIX = "/api/"


def is_jasmin_api_request(request) -> bool:
    return request._request.path_info.startswith(JASMIN_API_PATH_PREFIX)


class TapirSessionAuthentication(SessionAuthentication):
    """Tapir's session authentication, except on Jasmin's API: there, like in
    Jasmin itself, only Jasmin's JWT authenticates. Jasmin's frontend doesn't send
    the CSRF token that session authentication requires."""

    def authenticate(self, request):
        if is_jasmin_api_request(request):
            return None
        return super().authenticate(request)


class TapirForwardAuthentication(DrfForwardAuthentication):
    """See TapirSessionAuthentication."""

    def authenticate(self, request):
        if is_jasmin_api_request(request):
            return None
        return super().authenticate(request)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """For the views that issue Jasmin tokens from the Tapir session, which
    Jasmin's frontend calls without a CSRF token.

    Safe because Tapir's session cookie is SameSite=Lax: cross-site POST requests
    don't carry it. And the tokens are in the response body, which another site
    can't read."""

    def enforce_csrf(self, request):
        return None


class TapirSessionAuthenticationScheme(SessionScheme):
    target_class = TapirSessionAuthentication


class TapirForwardAuthenticationScheme(DrfForwardAuthenticationScheme):
    target_class = TapirForwardAuthentication


class CsrfExemptSessionAuthenticationScheme(SessionScheme):
    target_class = CsrfExemptSessionAuthentication
