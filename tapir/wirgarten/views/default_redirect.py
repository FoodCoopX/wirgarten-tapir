from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member


@require_http_methods(["GET"])
def wirgarten_redirect_view(request):
    # Not logged in
    if request.user.pk is None:
        return HttpResponseRedirect(reverse_lazy("login") + "?next=/")

    # User is Admin --> redirect to dashboard
    elif request.user.has_perm(Permission.Coop.VIEW):
        return HttpResponseRedirect(reverse_lazy("wirgarten:admin_dashboard"))

    # User is Member --> redirect to member detail view
    elif Member.objects.filter(pk=request.user.pk).exists():
        return HttpResponseRedirect(
            reverse_lazy("wirgarten:member_detail", kwargs={"pk": request.user.pk})
        )

    # User is TapirUser but not Member --> redirect to accounts/me
    else:
        return HttpResponseRedirect(reverse_lazy("accounts:index"))
