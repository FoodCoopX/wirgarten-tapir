from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from tapir.bakery.models import Bread


@require_GET
@login_required
def bread_picture(request, bread_id: str):
    bread = get_object_or_404(Bread, id=bread_id)
    if not bread.picture:
        raise Http404

    try:
        file = bread.picture.open("rb")
    except FileNotFoundError:
        raise Http404

    response = FileResponse(file)
    # The URL changes with every upload, see BreadPictureField.
    response["Cache-Control"] = "private, max-age=31536000, immutable"
    return response
