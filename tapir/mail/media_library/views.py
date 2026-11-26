"""
This is an example Django views.py file for use with the advanced version
of the django-drf-filepond tutorial (https://django-drf-filepond.\
    readthedocs.io/en/latest/index.html#document-tutorial/tutorial).

This file provides a single view class that handles post and delete requests
for demonstrating the handling of file storage and deletion using the
django-drf-filepond API.
"""

import datetime
import json
import logging
import os

from django.http import Http404
from django.http.response import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseServerError,
    FileResponse,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import View
from django_drf_filepond.api import store_upload, delete_stored_upload
from django_drf_filepond.models import TemporaryUpload, StoredUpload
from drf_spectacular.utils import extend_schema_view, extend_schema
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination

from tapir.mail.media_library.serializers import (
    TemporaryUploadSerializer,
    StoredUploadSerializer,
)

LOG = logging.getLogger(__name__)

CONTENT_TYPE_JSON = "application/json"


class ConfirmUploadView(View):
    # Handle POST request
    def post(self, request):
        # Get the post request and extract the IDs of the temporary upload(s)
        # to be permanently stored.
        data = request.POST
        try:
            filepond_ids = data.getlist("filepond")
        except KeyError:
            LOG.error("No filepond key found in submitted form.")
            return HttpResponseBadRequest("Missing filepond key in form.")

        if not isinstance(filepond_ids, list):
            LOG.error("Unexpected data type in form.")
            return HttpResponseBadRequest("Unexpected data type in form.")

        # Go through the list of IDs. For each, look up the associated temp
        # upload and call django-drf-filepond's API function store_upload.
        # This stores the file to a local or remote file store depending on
        # how the library is configured.
        stored_uploads = []
        for upload_id in filepond_ids:
            tu = TemporaryUpload.objects.get(upload_id=upload_id)
            LOG.debug("Storing upload: [%s]" % filepond_ids)
            store_upload(upload_id, os.path.join(upload_id, tu.upload_name))
            stored_uploads.append(upload_id)

        delete_abandoned_temporary_uploads()

        # Return the list of uploads that were stored.
        return HttpResponse(
            json.dumps({"status": "OK", "uploads": stored_uploads}),
            content_type=CONTENT_TYPE_JSON,
        )

    # Handle request to delete a stored upload
    def delete(self, request):
        # Get the ID of the stored upload to be deleted and look it up in
        # the database.
        upload_id = request.GET.get("id", None)
        try:
            su = StoredUpload.objects.get(upload_id=upload_id)
        except StoredUpload.DoesNotExist:
            return HttpResponseNotFound()

        # If we found the StoredUpload record, call the django-drf-filepond
        # API function delete_stored_upload to delete the record from the
        # database and delete the corresponding file on the local or remote
        # filesystem (delete_file=True).
        try:
            delete_stored_upload(su.upload_id, delete_file=True)
        except Exception as e:
            return HttpResponseServerError(
                json.dumps({"status": "ERROR", "errorMsg": str(e)}),
                content_type=CONTENT_TYPE_JSON,
            )

        return HttpResponse(
            json.dumps({"status": "OK", "deleted": upload_id}),
            content_type=CONTENT_TYPE_JSON,
        )


TEMPORARY_UPLOAD_MAX_AGE = datetime.timedelta(hours=24)


def delete_abandoned_temporary_uploads():
    TemporaryUpload.objects.filter(
        uploaded__lt=timezone.now() - TEMPORARY_UPLOAD_MAX_AGE
    ).delete()


@extend_schema_view(
    create=extend_schema(operation_id="temporaryuploads_create"),
    list=extend_schema(operation_id="temporaryuploads_list"),
    retrieve=extend_schema(operation_id="temporaryuploads_retrieve"),
    update=extend_schema(operation_id="temporaryuploads_update"),
    partial_update=extend_schema(operation_id="temporaryuploads_partial_update"),
    destroy=extend_schema(operation_id="temporaryuploads_destroy"),
)
class TemporaryUploadViewSet(viewsets.ModelViewSet):
    serializer_class = TemporaryUploadSerializer
    queryset = TemporaryUpload.objects.order_by("-uploaded")
    pagination_class = LimitOffsetPagination


@extend_schema_view(
    create=extend_schema(operation_id="storeduploads_create"),
    list=extend_schema(operation_id="storeduploads_list"),
    retrieve=extend_schema(operation_id="storeduploads_retrieve"),
    update=extend_schema(operation_id="storeduploads_update"),
    partial_update=extend_schema(operation_id="storeduploads_partial_update"),
    destroy=extend_schema(operation_id="storeduploads_destroy"),
)
class StoredUploadViewSet(viewsets.ModelViewSet):
    serializer_class = StoredUploadSerializer
    queryset = StoredUpload.objects.order_by("-stored")
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["file"]


def get_file_view(request, upload_id: str):
    stored_upload = get_object_or_404(StoredUpload, upload_id=upload_id)
    try:
        file = stored_upload.file.open("rb")
    except FileNotFoundError:
        LOG.warning(f"File missing from storage for upload {upload_id}")
        raise Http404
    return FileResponse(file, filename=stored_upload.file.name)
