from tapir.wirgarten.parameters import ParameterDefinitions
from django.urls import reverse
from django.core import mail

from tapir.mail.models import EmailConfigurationVersion
from tapir.mail.tests.factories import EmailConfigurationVersionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestEmailConfigurationVersionSendTestEmail(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self._login_as_admin()

    def test_emailConfigurationDoesNotExist_returns404(self):
        self.assertEqual(0, EmailConfigurationVersion.objects.count())
        response = self._send_request("abc", None)
        self.assertEqual(404, response.status_code)
        self.assertEqual(0, len(mail.outbox))

    def test_invalidFormData_returns400(self):
        EmailConfigurationVersionFactory.create()
        response = self._send_request(
            EmailConfigurationVersion.objects.first().id, {"invalid_parameter": "aaa"}
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual(0, len(mail.outbox))

    def test_validRequest_emailIsSent(self):
        subject = "TEST SUBJECT"
        EmailConfigurationVersionFactory.create(subject=subject)
        response = self._send_request(
            EmailConfigurationVersion.objects.first().id,
            {"recipients": ["test@test.com", "foo@bar.net"]},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(mail.outbox))
        sent_mail = mail.outbox[0]
        self.assertIn("This is a dummy email!", sent_mail.body)
        self.assertEqual(["test@test.com"], sent_mail.to)
        self.assertEqual(subject, sent_mail.subject)
        self.assertEqual(["foo@bar.net"], mail.outbox[1].to)

    def _send_request(
        self, email_configuration_version_id: str, post_data: dict | None
    ):
        return self.client.post(
            reverse(
                "emailconfigurationversion-send-test-email",
                args=[email_configuration_version_id],
            ),
            data=post_data,
            content_type="application/json",
        )
