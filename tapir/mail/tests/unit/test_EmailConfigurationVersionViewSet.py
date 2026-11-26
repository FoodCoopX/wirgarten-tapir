from types import SimpleNamespace
from unittest.mock import patch, Mock, call, MagicMock

from django.http import Http404
from rest_framework.response import Response
from tapir.mail.models import EmailConfigurationVersion
from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.mail.views.email_configurations import EmailConfigurationVersionViewSet


class TestEmailConfigurationVersion(TapirUnitTest):
    @patch("tapir.mail.views.email_configurations.get_object_or_404")
    def test_sendTestEmail_emailConfigurationDoesntExist_throwsException(
        self, mock_get_object_or_404: Mock
    ):
        exception_class = Http404
        mock_get_object_or_404.side_effect = exception_class("TestException")
        email_configuration_version_id = 123
        with self.assertRaises(exception_class):
            EmailConfigurationVersionViewSet().send_test_email(
                None, email_configuration_version_id
            )

    def test_sendTestMail_invalidRecipient_returns400Response(self):
        for recipients in [
            [],  # no recipients
            [["test@test.de", 1]],  # invalid recipient
        ]:
            with self.subTest(recipients=recipients):
                mock_request = Mock()
                mock_request.data.get.return_value = recipients
                email_configuration_version_id = 123
                patcher = patch(
                    "tapir.mail.views.email_configurations.get_object_or_404"
                )
                mock_get_object_or_404 = patcher.start()
                self.addCleanup(patcher.stop)

                response = EmailConfigurationVersionViewSet().send_test_email(
                    mock_request, email_configuration_version_id
                )

                mock_get_object_or_404.assert_called_once_with(
                    EmailConfigurationVersion, id=email_configuration_version_id
                )
                mock_request.data.get.assert_called_once_with("recipients", [])
                self.assertIsInstance(response, Response)
                self.assertEqual(400, response.status_code)

    @patch(
        "tapir.mail.views.email_configurations.replace_tokens",
        autospec=True,
        side_effect=lambda mjml, *_, **__: mjml,
    )
    @patch("tapir.mail.views.email_configurations.prepare_email")
    @patch("tapir.mail.views.email_configurations.get_object_or_404")
    def test_sendTestMail_validRecipient_sendsMailAndReturns200Response(
        self,
        mock_get_object_or_404: Mock,
        mock_prepare_mail: Mock,
        _: MagicMock,
    ):
        mock_request = Mock()
        recipients = ["test@test.de", "test2@mail.de"]
        mock_request.data.get.return_value = recipients
        email_configuration_version_id = 123
        email_configuration_version = SimpleNamespace(
            content="<mjml><mj-body><mj-text>Test Email<mj-body><mj-text></mjml>",
            subject="TEST_SUBJECT",
        )
        mock_get_object_or_404.return_value = email_configuration_version

        response = EmailConfigurationVersionViewSet().send_test_email(
            mock_request, email_configuration_version_id
        )

        mock_get_object_or_404.assert_called_once_with(
            EmailConfigurationVersion, id=email_configuration_version_id
        )
        mock_request.data.get.assert_called_once_with("recipients", [])
        self.assertIsInstance(response, Response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, mock_prepare_mail.call_count)
        mock_prepare_mail.assert_has_calls(
            [
                call(
                    mjml=email_configuration_version.content,
                    subject=email_configuration_version.subject,
                    recipients=["test@test.de"],
                ),
                call(
                    mjml=email_configuration_version.content,
                    subject=email_configuration_version.subject,
                    recipients=["test2@mail.de"],
                ),
            ],
            any_order=True,
        )
