from django.urls import reverse
from tapir.mail.tests.factories import EmailConfigurationVersionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestEmailConfigurationVersionListAndRetrieve(TapirIntegrationTest):
    def setUp(self) -> None:
        super().setUp()
        self._login_as_admin()

    def test_list_returns405(self):
        EmailConfigurationVersionFactory.create()
        response = self.client.get(reverse("emailconfigurationversion-list"))
        self.assertEqual(405, response.status_code)

    def test_retrieve_returns405(self):
        version = EmailConfigurationVersionFactory.create()
        response = self.client.get(
            reverse("emailconfigurationversion-detail", args=[version.id])
        )
        self.assertEqual(405, response.status_code)

    def test_getBundledInfo_stillWorks(self):
        version = EmailConfigurationVersionFactory.create()
        response = self.client.get(
            reverse("emailconfigurationversion-get-bundled-info", args=[version.id])
        )
        self.assertEqual(200, response.status_code)
