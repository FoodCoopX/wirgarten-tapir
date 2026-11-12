import mimetypes

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET
from django.views.generic import ListView

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import ExportedFile


class ExportedFilesListView(PermissionRequiredMixin, ListView):
    model = ExportedFile
    ordering = "-created_at"

    paginate_by = 50
    permission_required = Permission.Coop.VIEW

    def get_queryset(self):
        files = super().get_queryset()
        if not self.request.user.has_perm(Permission.Coop.MANAGE):
            files = files.filter(requires_coop_manage=False)
        return files


@require_GET
@csrf_protect
@permission_required(Permission.Coop.VIEW)
def download(request, pk):
    entity = get_object_or_404(ExportedFile, pk=pk)
    if entity.requires_coop_manage and not request.user.has_perm(
        Permission.Coop.MANAGE
    ):
        raise PermissionDenied
    filename = (
        f"{entity.name}_{entity.created_at.strftime('%Y%m%d_%H%M%S')}.{entity.type}"
    )
    mime_type, _ = mimetypes.guess_type(filename)
    response = FileResponse(
        entity.file, as_attachment=True, content_type=mime_type, filename=filename
    )
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response
