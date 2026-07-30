from weasyprint.urls import URLFetcher, FatalURLFetchingError


class TapirUrlFetcher(URLFetcher):
    def fetch(self, url, headers=None):
        if url.startswith("file:"):
            raise FatalURLFetchingError(
                f"For security reasons, it is not allowed to use file URLs in PDF-templates. The following url is forbidden: {url}"
            )
        return super().fetch(url, headers)
