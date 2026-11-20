from unittest.mock import patch, Mock

from django.http import Http404

from tapir.core.services.member_extra_email_confirmation_link_service import (
    MemberExtraEmailConfirmationLinkService,
)
from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberExtraEmailConfirmationLinkService(TapirIntegrationTest):
    def setUp(self):
        super().setUp()
        self.extra_email = MemberExtraEmail.objects.create(
            member=MemberFactory.create(), email="test@example.com"
        )

    def test_getExtraEmailFromToken_default_returnsTheExtraEmail(self):
        token = MemberExtraEmailConfirmationLinkService.build_token(self.extra_email)

        self.assertEqual(
            self.extra_email,
            MemberExtraEmailConfirmationLinkService.get_extra_email_from_token(token),
        )

    @patch("django.core.signing.time.time")
    def test_getExtraEmailFromToken_linkIsOlderThanTheValidity_raises404(
        self, mock_time: Mock
    ):
        mock_time.return_value = 1_800_000_000
        token = MemberExtraEmailConfirmationLinkService.build_token(self.extra_email)
        mock_time.return_value = 1_800_000_000 + 8 * 24 * 60 * 60

        with self.assertRaises(Http404):
            MemberExtraEmailConfirmationLinkService.get_extra_email_from_token(token)

    def test_getExtraEmailFromToken_tokenWasChanged_raises404(self):
        token = MemberExtraEmailConfirmationLinkService.build_token(self.extra_email)
        other_extra_email = MemberExtraEmail.objects.create(
            member=MemberFactory.create(), email="other@example.com"
        )
        changed_token = token.replace(self.extra_email.id, other_extra_email.id, 1)

        with self.assertRaises(Http404):
            MemberExtraEmailConfirmationLinkService.get_extra_email_from_token(
                changed_token
            )

    def test_getExtraEmailFromToken_extraEmailWasDeleted_raises404(self):
        token = MemberExtraEmailConfirmationLinkService.build_token(self.extra_email)
        self.extra_email.delete()

        with self.assertRaises(Http404):
            MemberExtraEmailConfirmationLinkService.get_extra_email_from_token(token)
