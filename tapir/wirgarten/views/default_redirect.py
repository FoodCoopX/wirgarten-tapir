from django.utils.translation import gettext_lazy as _

from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member


class RequestUserType:
    ANONYMOUS = 0
    MEMBER = 1
    STAFF = 2


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


def handle_403(request, exception):
    user_type = get_user_type(request)
    if user_type == RequestUserType.ANONYMOUS:
        return HttpResponseRedirect(reverse_lazy("login"))
    if user_type == RequestUserType.MEMBER:
        return HttpResponseRedirect(
            reverse_lazy("wirgarten:member_detail", kwargs={"pk": request.user.id})
        )
    if user_type == RequestUserType.STAFF:
        return HttpResponse(
            _("Du bist nicht authorisiert diese Seite zu sehen."), status=403
        )


@require_http_methods(["GET"])
def wirgarten_redirect_view(request):
    user_type = get_user_type(request)

    if user_type == RequestUserType.ANONYMOUS:
        return HttpResponseRedirect(reverse_lazy("login"))

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

    return handle_403(
        request, PermissionError(_("Du bist nicht authorisiert diese Seite zu sehen."))
    )
