import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.bakery.serializers import BreadListSerializer
from tapir.bakery.tests.factories import BreadFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

PICTURE_CONTENT = b"fake-image-bytes"


class TestBreadPictureView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.media_root = tempfile.mkdtemp()
        media_override = override_settings(MEDIA_ROOT=self.media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.client.force_login(MemberFactory.create())

    def create_bread_with_picture(self):
        return BreadFactory.create(
            picture=SimpleUploadedFile("roggen.png", PICTURE_CONTENT)
        )

    def test_get_breadHasPicture_returnsFile(self):
        bread = self.create_bread_with_picture()

        response = self.client.get(reverse("bakery:bread-picture", args=[bread.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), PICTURE_CONTENT)

    def test_get_breadHasNoPicture_returns404(self):
        bread = BreadFactory.create()

        response = self.client.get(reverse("bakery:bread-picture", args=[bread.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_fileMissingOnDisk_returns404(self):
        bread = self.create_bread_with_picture()
        os.remove(bread.picture.path)

        response = self.client.get(reverse("bakery:bread-picture", args=[bread.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_unknownBread_returns404(self):
        response = self.client.get(reverse("bakery:bread-picture", args=["unknown"]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_unauthenticated_redirectsToLogin(self):
        bread = self.create_bread_with_picture()
        self.client.logout()

        response = self.client.get(reverse("bakery:bread-picture", args=[bread.id]))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_serializer_breadHasPicture_returnsUrlOfPictureView(self):
        bread = self.create_bread_with_picture()

        picture_url = BreadListSerializer(bread).data["picture"]

        file_name = bread.picture.name.rsplit("/", 1)[-1]
        self.assertEqual(
            picture_url,
            f"{reverse('bakery:bread-picture', args=[bread.id])}?v={file_name}",
        )

    def test_serializer_breadHasNoPicture_returnsNone(self):
        bread = BreadFactory.create()

        self.assertIsNone(BreadListSerializer(bread).data["picture"])
