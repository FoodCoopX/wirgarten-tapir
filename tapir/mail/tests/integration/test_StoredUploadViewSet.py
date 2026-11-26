import shortuuid
from django.urls import reverse
from django.utils import timezone
from django_drf_filepond.models import StoredUpload

from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class StoredUploadViewSetTest(TapirIntegrationTest):
    def setUp(self) -> None:
        super().setUp()
        self._login_as_admin()

    def create_stored_upload(self, file_name: str):
        upload_id = shortuuid.uuid()
        StoredUpload.objects.create(
            upload_id=upload_id,
            file=f"{upload_id}/{file_name}",
            uploaded=timezone.now(),
        )
        return upload_id

    def test_list_searchGiven_returnsOnlyMatchingFileNames(self):
        matching_id = self.create_stored_upload("Newsletter-Banner.png")
        self.create_stored_upload("logo.png")

        response = self.client.get(
            reverse("storedupload-list"), {"search": "banner", "limit": 10}
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(1, response.json()["count"])
        self.assertEqual(matching_id, response.json()["results"][0]["upload_id"])

    def test_list_loggedInAsNormalUser_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("storedupload-list"))

        self.assertStatusCode(response, 403)
