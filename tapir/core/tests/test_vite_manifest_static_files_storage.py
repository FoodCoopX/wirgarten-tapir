from django.core.files.base import ContentFile

from tapir.core.vite_manifest_static_files_storage import (
    ViteManifestStaticFilesStorage,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestViteManifestStaticFilesStorage(TapirUnitTest):
    def test_hashedName_mainFrontendAsset_nameUnchanged(self):
        storage = ViteManifestStaticFilesStorage()

        hashed_name = storage.hashed_name(
            name="assets/dashboard-ClSDOF5M.js", content=ContentFile(b"content")
        )

        self.assertEqual("assets/dashboard-ClSDOF5M.js", hashed_name)

    def test_hashedName_mailFrontendAsset_nameUnchanged(self):
        storage = ViteManifestStaticFilesStorage()

        hashed_name = storage.hashed_name(
            name="mail/assets/main-vW_sFhU5.js", content=ContentFile(b"content")
        )

        self.assertEqual("mail/assets/main-vW_sFhU5.js", hashed_name)

    def test_hashedName_otherFile_nameHashed(self):
        storage = ViteManifestStaticFilesStorage()

        hashed_name = storage.hashed_name(
            name="core/css/base.css", content=ContentFile(b"content")
        )

        self.assertEqual("core/css/base.9a0364b9e99b.css", hashed_name)
