import mimetypes

from django.contrib.auth.decorators import permission_required
from django.http import FileResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET
from django.views.generic import ListView

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import ExportedFile


class ExportedFilesListView(ListView):
    model = ExportedFile
    ordering = "-created_at"

    paginate_by = 50
    permission_required = Permission.Coop.VIEW


@require_GET
@csrf_protect
@permission_required(Permission.Coop.VIEW)
def download(request, pk):
    entity = ExportedFile.objects.get(pk=pk)
    filename = (
        f"{entity.name}_{entity.created_at.strftime('%Y%m%d_%H%M%S')}.{entity.type}"
    )
    mime_type, _ = mimetypes.guess_type(filename)
    response = FileResponse(
        entity.file, as_attachment=True, content_type=mime_type, filename=filename
    )
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response
