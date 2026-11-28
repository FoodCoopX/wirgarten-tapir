from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.core.files import File


class ViteManifestStaticFilesStorage(ManifestStaticFilesStorage):
    # Vite (the frontend's builder) already adds hashes to it's file names, and its chunks import each other by those names.
    # If we hashed them again with hashed_name(), the browser would load the same module twice under two URLs.
    # So we skip the folders that Vite produces.
    VITE_ASSET_DIRECTORIES = ("assets/", "mail/assets/")

    def hashed_name(
        self, name: str, content: File | None = None, filename: str | None = None
    ):
        if name.startswith(self.VITE_ASSET_DIRECTORIES):
            return name
        return super().hashed_name(name, content=content, filename=filename)
