from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from tapir.accounts.models import TapirUser
from tapir.log.forms import CreateTextLogEntryForm
from tapir.log.models import EmailLogEntry, TextLogEntry
from tapir.log.util import freeze_for_log
from tapir.utils.shortcuts import safe_redirect


@require_GET
@permission_required("coop.manage")
def email_log_entry_content(request, pk):
    log_entry = get_object_or_404(EmailLogEntry, pk=pk)

    response = HttpResponse(content_type="text/html")
    response.write(log_entry.email_content)
    return response


class UpdateViewLogMixin:
    def get_object(self, *args, **kwargs):
        result = super().get_object(*args, **kwargs)
        self.old_object_frozen = freeze_for_log(result)
        return result


@require_POST
@permission_required("coop.manage")
def create_text_log_entry(request, **kwargs):
    user = TapirUser.objects.filter(pk=kwargs.get("user_pk")).first()
    # share_owner = ShareOwner.objects.filter(pk=kwargs.get("shareowner_pk")).first()

    log_entry = TextLogEntry().populate(
        actor=request.user, user=user  # , share_owner=share_owner
    )

    form = CreateTextLogEntryForm(request.POST, instance=log_entry)

    if not form.is_valid():
        return HttpResponseBadRequest(str(form.errors))

    form.save()
    return safe_redirect(request.GET.get("next"), "/", request)
