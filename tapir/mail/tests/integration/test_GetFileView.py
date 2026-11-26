from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from django_drf_filepond.models import StoredUpload

from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class GetFileViewTest(TapirIntegrationTest):
    def test_getFileView_uploadDoesNotExist_returns404(self):
        response = self.client.get(reverse("get_file", args=["unknown"]))

        self.assertStatusCode(response, 404)

    def test_getFileView_fileMissingFromStorage_returns404(self):
        StoredUpload.objects.create(
            upload_id="missingfile0000000000a",
            file="does_not_exist.png",
            uploaded=timezone.now(),
        )

        response = self.client.get(reverse("get_file", args=["missingfile0000000000a"]))

        self.assertStatusCode(response, 404)

    def test_getFileView_fileExists_returnsFileContent(self):
        stored_upload = StoredUpload(
            upload_id="existingfile000000000a", uploaded=timezone.now()
        )
        stored_upload.file.save("test_get_file_view.txt", ContentFile(b"content"))
        self.addCleanup(stored_upload.file.storage.delete, stored_upload.file.name)

        response = self.client.get(reverse("get_file", args=["existingfile000000000a"]))

        self.assertEqual(200, response.status_code)
        self.assertEqual(b"content", b"".join(response.streaming_content))
