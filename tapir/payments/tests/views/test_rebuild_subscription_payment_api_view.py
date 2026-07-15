import datetime
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status

from tapir.payments.services.pain_008_xml_generator import Pain008XmlGenerator
from tapir.wirgarten.models import PaymentTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    mock_timezone,
)


class TestRebuildSubscriptionPaymentsApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2023, month=1, day=1),
        )
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN, value="NL23INGB1878166956"
        )
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, value="test_id"
        )

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2023, month=4, day=15)
        )

    def test_post_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self._setup_data_and_do_call()

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertEqual(0, PaymentTransaction.objects.count())

    def test_post_loggedInAsAdmin_rebuildsPayments(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self._setup_data_and_do_call()
        self.assert_order_confirmed(response.json())

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(2, PaymentTransaction.objects.count())

    @patch.object(Pain008XmlGenerator, "build_xml_string", autospec=True)
    def test_post_xmlExportThrowsError_returnsErrorProperly(
        self, mock_build_xml_string: Mock
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        mock_build_xml_string.side_effect = ValidationError("Test error")

        response = self._setup_data_and_do_call()

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual("Test error", response_content["error"])
        self.assertEqual(0, PaymentTransaction.objects.count())

    def _setup_data_and_do_call(self):
        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2023, month=1, day=1),
            member__sepa_consent=self.now,
        )
        ProductPriceFactory.create(
            product=subscription.product, valid_from=subscription.start_date
        )

        url = reverse("payments:rebuild_subscription_payments")
        url = f"{url}?from=2023-04-25"
        return self.client.post(url)
