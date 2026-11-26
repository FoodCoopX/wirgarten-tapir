from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import URLPattern, URLResolver

from tapir.mail import urls as mail_urls
from tapir.mail.permissions import HasEmailManagePermission
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.tests.test_utils import TapirUnitTest

PUBLIC_URL_NAMES = {
    "tracking-track",
    "get_file",
    "category_registration_external_form",
    "confirmation_mail_sent",
    "user_confirms_registration",
    "confirmation_registration_complete",
    "external_recipient_manager",
}


class TestMailUrlPermissions(TapirUnitTest):
    def test_mailUrls_nonPublicUrl_requiresEmailManagePermission(self):
        for route, pattern in self._get_url_patterns(
            patterns=mail_urls.urlpatterns, prefix=""
        ):
            if pattern.name in PUBLIC_URL_NAMES:
                continue
            with self.subTest(route=route):
                self.assertTrue(
                    self._requires_email_manage_permission(pattern),
                    f"The mail URL '{route}' must require {Permission.Email.MANAGE} or be listed in PUBLIC_URL_NAMES.",
                )

    def test_publicUrlNames_default_allExistInMailUrls(self):
        url_names = {
            pattern.name
            for _, pattern in self._get_url_patterns(
                patterns=mail_urls.urlpatterns, prefix=""
            )
        }

        self.assertEqual(set(), PUBLIC_URL_NAMES - url_names)

    @classmethod
    def _get_url_patterns(cls, patterns: list, prefix: str):
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                yield from cls._get_url_patterns(
                    patterns=pattern.url_patterns, prefix=prefix + str(pattern.pattern)
                )
            elif isinstance(pattern, URLPattern):
                yield prefix + str(pattern.pattern), pattern

    @staticmethod
    def _requires_email_manage_permission(pattern: URLPattern) -> bool:
        drf_view_class = getattr(pattern.callback, "cls", None)
        if drf_view_class is not None:
            return HasEmailManagePermission in drf_view_class.permission_classes

        django_view_class = getattr(pattern.callback, "view_class", None)
        if django_view_class is not None:
            return (
                issubclass(django_view_class, PermissionRequiredMixin)
                and django_view_class.permission_required == Permission.Email.MANAGE
            )

        return False
