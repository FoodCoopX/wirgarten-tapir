from unittest.mock import patch, Mock

from django.test import override_settings
from django.urls import reverse
from mailmanclient import MailmanConnectionError

from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True)
class TestMailingListBaseView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(TapirMailmanClient, "ensure_instance_domain_exists", autospec=True)
    def test_get_default_ensuresDomainExists(
        self, mock_ensure_instance_domain_exists: Mock
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(reverse("core:mailing_lists"))

        self.assertEqual(200, response.status_code)
        self.assertFalse(response.context_data["show_connection_error"])
        mock_ensure_instance_domain_exists.assert_called_once()

    @override_settings(MAILING_LISTS_ENABLED=False)
    @patch.object(TapirMailmanClient, "ensure_instance_domain_exists", autospec=True)
    def test_get_mailingListsDisabled_returns403(
        self, mock_ensure_instance_domain_exists: Mock
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(reverse("core:mailing_lists"))

        self.assertEqual(403, response.status_code)
        mock_ensure_instance_domain_exists.assert_not_called()

    @patch.object(TapirMailmanClient, "ensure_instance_domain_exists", autospec=True)
    def test_get_loggedInAsNormalMember_returns403(
        self, mock_ensure_instance_domain_exists: Mock
    ):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("core:mailing_lists"))

        self.assertEqual(403, response.status_code)
        mock_ensure_instance_domain_exists.assert_not_called()

    @patch.object(TapirMailmanClient, "ensure_instance_domain_exists", autospec=True)
    def test_get_mailmanConnectionFails_showError(
        self, mock_ensure_instance_domain_exists: Mock
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mock_ensure_instance_domain_exists.side_effect = MailmanConnectionError(
            "test error"
        )
        response = self.client.get(reverse("core:mailing_lists"))

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.context_data["show_connection_error"])
        mock_ensure_instance_domain_exists.assert_called_once()
