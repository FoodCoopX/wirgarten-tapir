import datetime
import unittest
from unittest.mock import patch

import factory.random
from django.core.cache import cache
from django.test import TestCase, Client, SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import parameter_definition
from tapir.wirgarten.parameters import Parameter
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


def set_bypass_keycloak(bypass: bool = True):
    parameter_definition(
        key=Parameter.MEMBER_BYPASS_KEYCLOAK,
        label="Bypass Keycloak",
        datatype=TapirParameterDatatype.BOOLEAN,
        initial_value=True,
        description="Test",
        category="Test",
    )
