"""Every place where Tapir relies on Jasmin internals rather than on its public
API. To check on each Jasmin update."""

from apps.accounts.services import auth_service as jasmin_auth_service
from apps.accounts.views import auth_views as jasmin_auth_views

# The localStorage key under which Jasmin's frontend caches the logged-in user,
# see AuthMetadata in react-core/src/shared/contexts/AuthContext.tsx.
AUTH_METADATA_LOCAL_STORAGE_KEY = "auth"


def issue_login_payload(user, tenant) -> tuple[dict, str]:
    """Issues Jasmin tokens for the user, like Jasmin's login view does.

    Returns the login response's payload and the refresh token."""
    login_result = jasmin_auth_service._issue_login_tokens(user=user, tenant=tenant)
    payload = jasmin_auth_views._login_payload(result=login_result, tenant=tenant)
    return payload, login_result.refresh


def build_auth_metadata(user, tenant) -> dict:
    """What Jasmin's frontend stores in localStorage after a login.

    With it in place before the frontend starts, the frontend knows the user and
    their roles without showing its login page; its boot refresh then gets the
    access token from Tapir's session, see JasminRefreshVew. Built like the login
    response's user, but without issuing tokens."""
    member_profile = getattr(user, "member_profile", None)
    linked_reseller = getattr(user, "linked_reseller", None)
    login_result = jasmin_auth_service.LoginResult(
        user=user,
        access="",
        refresh="",
        member_id=member_profile.id if member_profile else None,
        reseller_id=linked_reseller.id if linked_reseller else None,
    )
    payload = jasmin_auth_views._login_payload(result=login_result, tenant=tenant)
    return {"user": payload["user"]}
