import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.models import PaymentTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    ProductPriceFactory,
    MemberPickupLocationFactory,
    GrowingPeriodFactory,
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
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1)
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

    def test_post_xmlExportThrowsError_returnsErrorProperly(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        self._set_parameter(key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, value="")

        response = self._setup_data_and_do_call()

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Der Parameter 'Gläubiger-Identifikationsnummer' muss in der Konfig gesetzt werden",
            response_content["error"],
        )
        self.assertEqual(0, PaymentTransaction.objects.count())

    def test_post_somePaymentsFail_returnsErrorProperly(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        subscription_1 = SubscriptionFactory.create(
            period=self.growing_period,
            member__account_owner=None,
            member__first_name="John",
            member__last_name="Test1",
            member__member_no=12,
        )
        SubscriptionFactory.create(
            period=self.growing_period,
            member__iban="INVALID_IBAN",
            product=subscription_1.product,
            member__first_name="Alice",
            member__last_name="Test2",
            member__member_no=902,
        )
        ProductPriceFactory.create(
            product=subscription_1.product, valid_from=subscription_1.start_date
        )

        response = self._setup_data_and_do_call()

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Die Lastschriften konnten neu erzeugt werden, es sind aber folgenden Fehler aufgetreten. Die betroffene Mitglieder sind nicht in der neue Dateien enthalten. Mitglied Alice Test2 #902: IN is not a valid country code for IBAN., Mitglied John Test1 #12 hat kein Kontoinhaber",
            response_content["error"],
        )
        self.assertEqual(2, PaymentTransaction.objects.count())

    def _setup_data_and_do_call(self):
        subscription = SubscriptionFactory.create(
            period=self.growing_period,
            member__sepa_consent=self.now,
        )
        ProductPriceFactory.create(
            product=subscription.product, valid_from=subscription.start_date
        )
        MemberPickupLocationFactory.create(
            member=subscription.member,
            valid_from=datetime.date(year=2023, month=1, day=1),
        )

        url = reverse("payments:rebuild_subscription_payments")
        url = f"{url}?from=2023-04-25"
        return self.client.post(url)
