import datetime
import unittest
from unittest.mock import patch, Mock

import factory.random
from django.core.cache import cache
from django.test import TestCase, Client, SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from tapir.wirgarten.tapirmail import configure_mail_module


class TapirFactoryMixin:
    def factory_setup(self) -> None:
        factory.random.reseed_random(self.__class__.__name__)


class TapirIntegrationTest(TapirFactoryMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.factory_setup()
        self.client = Client()
        self.apiClient = APIClient()
        cache.clear()
        configure_mail_module()
        mock_keycloak(self)

    def assertStatusCode(self, response, expected_status_code):
        self.assertEqual(
            expected_status_code,
            response.status_code,
            f"Unexpected status code, response content : {response.content.decode()}",
        )


class TapirUnitTest(TapirFactoryMixin, SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.factory_setup()


def mock_timezone(test: unittest.TestCase, now: datetime.datetime) -> datetime.datetime:
    now = timezone.make_aware(now) if timezone.is_naive(now) else now

    # Patch for timezone.now()
    if not hasattr(test, "mock_now"):
        patcher_now = patch("django.utils.timezone.now")
        test.mock_now = patcher_now.start()
        test.addCleanup(patcher_now.stop)
    test.mock_now.return_value = now

    # Patch for timezone.localdate()
    if not hasattr(test, "mock_localdate"):
        patcher_localdate = patch("django.utils.timezone.localdate")
        test.mock_localdate = patcher_localdate.start()
        test.addCleanup(patcher_localdate.stop)
    test.mock_localdate.return_value = now.date()

    return now


class TapirMockKeycloakException(Exception):
    pass


def mock_keycloak(test: TapirIntegrationTest):
    patcher_keycloak = patch(
        "tapir.accounts.services.keycloak_user_manager.KeycloakUserManager.get_keycloak_client"
    )
    test.mock_get_keycloak_client = patcher_keycloak.start()
    test.addCleanup(patcher_keycloak.stop)

    mock_client = Mock()
    test.mock_get_keycloak_client.return_value = mock_client

    keycloak_ids = {}
    mock_client.get_user_id.side_effect = lambda email: keycloak_ids.get(email, None)

    mock_client.create_user.side_effect = (
        lambda data: mock_set_and_return_new_keycloak_id(
            email=data["email"], keycloak_ids=keycloak_ids
        )
    )

    mock_client.delete_user.side_effect = lambda keycloak_id: delete_user(
        keycloak_id_to_delete=keycloak_id, keycloak_ids=keycloak_ids
    )


def mock_set_and_return_new_keycloak_id(email: str, keycloak_ids: dict) -> str:
    if email in keycloak_ids.keys():
        raise TapirMockKeycloakException(
            f"This email address is already in use: {email}"
        )
    keycloak_ids[email] = f"Mock Keycloak ID for {email}"
    return keycloak_ids[email]


def delete_user(keycloak_id_to_delete: str, keycloak_ids: dict):
    found_email = None
    for email, keycloak_id in keycloak_ids.items():
        if keycloak_id == keycloak_id_to_delete:
            found_email = email
            break
    if not found_email:
        raise TapirMockKeycloakException(
            f"No email found for keycloak ID {keycloak_id_to_delete}"
        )
    del keycloak_ids[found_email]
