import logging
import time

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from jwt import decode
from keycloak import KeycloakOpenID

from tapir.accounts.models import TapirUser

logger = logging.getLogger(__name__)


class KeycloakMiddleware(MiddlewareMixin):
    """KeyCloak Middleware for authentication and authorization."""

    def __init__(self, get_response):
        """One-time initialization of middleware."""
        self.get_response = get_response  # Required by django
        try:
            self.setup_keycloak()
        except Exception:
            raise Exception(
                f"{__name__}: Failed to set up keycloak connection."
                "Please check settings.KEYCLOAK."
            )

    def setup_keycloak(self):
        """Set up KeyCloakOpenID with given settings."""
        self.config = settings.KEYCLOAK_ADMIN_CONFIG
        self.keycloak = KeycloakOpenID(
            server_url=self.config["PUBLIC_URL"],
            realm_name=self.config["REALM_NAME"],
            client_id=self.config["FRONTEND_CLIENT_ID"],
        )

    def __call__(self, request):
        """Handle default requests."""
        return self.get_response(request)  # Required by django

    def auth_failed(self, log_message, error):
        """Return authentication failed message in log and API."""
        logger.debug(f"{log_message}: {repr(error)}")

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Check for authentication and try to get user from keycloak."""
        # Return unauthenticated request if no authorization is found
        if "token" not in request.COOKIES:
            logger.debug(f"No authorization found. Using public user.")
            return None

        # Retrieve token and user or return failure message
        access_token = request.COOKIES.get("token")

        # Decode token
        try:
            data = decode(access_token, options={"verify_signature": False})
            if data["exp"] < int(time.time()):
                return self.auth_failed("Token expired on: ", data["exp"])
        except Exception as e:
            return self.auth_failed("Could not decode token", e)

        # Add user to request
        keycloak_id = data.get("sub", None)
        if keycloak_id is None:
            return self.auth_failed("Could not get id from token: ", data)
        try:
            request.user = user = TapirUser.objects.get(keycloak_id=keycloak_id)
            user.email_verified = data.get("email_verified", False)

            roles = data.get("realm_access", {}).get("roles", [])

            user.roles = []
            for role in roles:
                if role not in settings.KEYCLOAK_NON_TAPIR_ROLES:
                    user.roles.append(role)
        except Exception as e:
            return self.auth_failed("Could not find matching TapirUser", e)

        # Return authenticated request if no exception is thrown
        return None
