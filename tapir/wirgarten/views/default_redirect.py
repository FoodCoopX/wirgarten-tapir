import inspect

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.utils.module_loading import import_string
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.constants import Permission


class RequestUserType:
    ANONYMOUS = 0
    MEMBER = 1
    STAFF = 2


def dynamic_view(view_key: str):
    resolved_view = settings.VIEWS.get(view_key, None)

    if resolved_view is None:
        print(f"ERROR: No view found for key: {view_key}. Check settings.py!")
        return HttpResponse(status=404)

    view_function = import_string(resolved_view)

    @require_http_methods(["GET", "POST"])
    def view(request, **kwargs):
        return view_function.as_view()(request, **kwargs)

    return view_function if inspect.isfunction(view_function) else view


@require_http_methods(["GET"])
def wirgarten_redirect_view(request):
    user_type = get_user_type(request)

    # User is Admin --> redirect to dashboard
    if user_type == RequestUserType.STAFF:
        return HttpResponseRedirect(reverse_lazy("wirgarten:admin_dashboard"))

    # User is Member --> redirect to member detail view
    if user_type == RequestUserType.MEMBER:
        return HttpResponseRedirect(
            reverse_lazy("wirgarten:member_detail", kwargs={"pk": request.user.id})
            + "?"
            + request.environ["QUERY_STRING"]
        )

    return HttpResponseRedirect(reverse("openid_connect_login", args=["keycloak"]))


def get_user_type(request) -> int:
    # Not authenticated
    if request.user is None or request.user.id is None:
        return RequestUserType.ANONYMOUS
    # User is Admin
    elif request.user.has_perm(Permission.Coop.VIEW):
        return RequestUserType.STAFF
    # User is Member
    else:
        return RequestUserType.MEMBER
