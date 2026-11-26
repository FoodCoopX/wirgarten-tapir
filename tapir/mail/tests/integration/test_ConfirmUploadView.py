import datetime
import os

import shortuuid

from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from django_drf_filepond.models import StoredUpload, TemporaryUpload

from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class ConfirmUploadViewTest(TapirIntegrationTest):
    def setUp(self) -> None:
        super().setUp()
        self._login_as_admin()

    def create_temporary_upload(self, age: datetime.timedelta):
        upload_id = shortuuid.uuid()
        temporary_upload = TemporaryUpload(
            upload_id=upload_id,
            file_id=upload_id,
            upload_name=f"{upload_id}.txt",
            upload_type=TemporaryUpload.FILE_DATA,
        )
        temporary_upload.file.save(upload_id, ContentFile(b"content"))
        TemporaryUpload.objects.filter(upload_id=upload_id).update(
            uploaded=timezone.now() - age
        )
        self.addCleanup(
            lambda: TemporaryUpload.objects.filter(upload_id=upload_id).delete()
        )
        return upload_id

    def test_post_default_storesUploadAndDeletesOnlyAbandonedTemporaryUploads(
        self,
    ):
        confirmed_id = self.create_temporary_upload(datetime.timedelta(minutes=1))
        recent_id = self.create_temporary_upload(datetime.timedelta(hours=23))
        self.create_temporary_upload(datetime.timedelta(hours=25))

        response = self.client.post(
            reverse("confirm_upload"), {"filepond": confirmed_id}
        )

        self.assertStatusCode(response, 200)
        stored_upload = StoredUpload.objects.get(upload_id=confirmed_id)
        self.addCleanup(os.rmdir, os.path.dirname(stored_upload.file.path))
        self.addCleanup(stored_upload.file.storage.delete, stored_upload.file.name)
        self.assertEqual(
            {recent_id},
            set(TemporaryUpload.objects.values_list("upload_id", flat=True)),
        )
