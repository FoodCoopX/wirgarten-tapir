import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    NOW,
    MemberFactory,
    PaymentFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetCashflowChartData(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, NOW)
        self._set_parameter(key=ParameterKeys.PAYMENT_DUE_DAY, value=10)

    def test_getCashflowChartData_notLoggedIn_returns403(self):
        response = self.client.get(reverse("wirgarten:admin_dashboard_cashflow_data"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_getCashflowChartData_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("wirgarten:admin_dashboard_cashflow_data"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_getCashflowChartData_noSubscriptions_returnsSingleMonth(self):
        self._login_as_admin()

        response = self.client.get(reverse("wirgarten:admin_dashboard_cashflow_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(["10.04.2023"], response.json()["labels"])
        self.assertEqual([0], response.json()["data"])

    @patch.object(MonthPaymentBuilder, "build_payments_for_month", autospec=True)
    def test_getCashflowChartData_default_returnsSumOfGeneratedAndExistingPaymentsPerMonth(
        self, mock_build_payments_for_month: Mock
    ):
        self._login_as_admin()
        SubscriptionFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=6, day=30),
        )
        PaymentFactory.create(
            due_date=datetime.date(year=2023, month=5, day=10), amount=30
        )
        PaymentFactory.create(
            due_date=datetime.date(year=2023, month=5, day=20), amount=5.5
        )
        PaymentFactory.create(
            due_date=datetime.date(year=2023, month=8, day=10), amount=1000
        )
        generated_amounts_by_month = {
            4: [10, 20],
            5: [40],
            6: [],
            7: [7],
        }
        mock_build_payments_for_month.side_effect = (
            lambda reference_date, cache, generated_payments: [
                PaymentFactory.build(amount=amount)
                for amount in generated_amounts_by_month[reference_date.month]
            ]
        )

        response = self.client.get(reverse("wirgarten:admin_dashboard_cashflow_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            ["10.04.2023", "10.05.2023", "10.06.2023", "10.07.2023"],
            response.json()["labels"],
        )
        self.assertEqual([30, 75.5, 0, 7], response.json()["data"])

    @patch.object(MonthPaymentBuilder, "build_payments_for_month", autospec=True)
    def test_getCashflowChartData_default_passesPaymentsGeneratedInPreviousMonthsToBuilder(
        self, mock_build_payments_for_month: Mock
    ):
        self._login_as_admin()
        SubscriptionFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=5, day=31),
        )
        payments_by_month = {
            4: PaymentFactory.build(amount=10),
            5: PaymentFactory.build(amount=20),
            6: PaymentFactory.build(amount=30),
        }
        already_generated_payments_by_month = {}

        def build_payments_for_month(reference_date, cache, generated_payments):
            already_generated_payments_by_month[reference_date.month] = set(
                generated_payments
            )
            return [payments_by_month[reference_date.month]]

        mock_build_payments_for_month.side_effect = build_payments_for_month

        self.client.get(reverse("wirgarten:admin_dashboard_cashflow_data"))

        self.assertEqual(
            {
                4: set(),
                5: {payments_by_month[4]},
                6: {payments_by_month[4], payments_by_month[5]},
            },
            already_generated_payments_by_month,
        )
