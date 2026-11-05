import datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.urls import reverse

from tapir.associations.models import (
    AssociationDeposit,
    AssociationDepositBooking,
    AssociationDepositLogEntry,
)
from tapir.associations.services.association_deposit_service import (
    AssociationDepositService as Deposits,
)
from tapir.associations.services.deposit_configuration import DepositConfiguration
from tapir.associations.services.deposit_payment_exporter import DepositPaymentExporter
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlSinglePaymentException,
    Pain008XmlGlobalException,
)
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentTransactionFactory,
    ExportedFileFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_today


class TestAssociationDepositService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.config = {
            **DepositConfiguration.get({}),
            "enabled": True,
            "allow_hardship": True,
        }
        self.config_patch = patch.object(
            DepositConfiguration, "get", return_value=self.config
        )
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.member = MemberFactory(iban="DE89370400440532013000")
        self.admin = MemberFactory(is_superuser=True)
        self.today = get_today({})
        AssociationMembershipFactory(member=self.member, start_date=self.today)

    def apply(self, action="agreement", amount="200.00", request_id=None, **kwargs):
        return Deposits.apply(
            member=self.member,
            actor=self.admin,
            cache={},
            administrative=True,
            request_id=request_id or str(uuid4()),
            data={
                "action": action,
                "amount": amount,
                "note": "Vereinbarung bestätigt",
                **kwargs,
            },
        )

    def mark_paid(self, payment):
        payment.status = Payment.PaymentStatus.PAID
        payment.transaction = PaymentTransactionFactory()
        payment.due_date = self.today
        payment.save()

    def test_regular_amount_validation(self):
        for amount in ["200", "250", "350"]:
            Deposits.validate_signup(amount, False, True, {})
        for amount in [
            "0",
            "199.99",
            "201",
            "249.99",
            "-1",
            "NaN",
            "Infinity",
            "200.001",
            "1000000",
        ]:
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                Deposits.validate_signup(amount, False, True, {})

    def test_hardship_creates_no_debt_or_payment(self):
        deposit = Deposits.register(
            self.member, 0, True, True, self.today, self.member, {}
        )
        self.assertTrue(deposit.hardship_pending)
        self.assertIsNone(deposit.agreed_amount)
        self.assertFalse(deposit.payments.exists())
        self.assertFalse(deposit.exception_authorized)
        self.assertEqual(1, AssociationDepositLogEntry.objects.count())

    def test_hardship_cannot_hide_self_approved_reduction(self):
        with self.assertRaises(ValidationError):
            Deposits.register(self.member, 100, True, True, self.today, self.member, {})
        self.assertFalse(AssociationDeposit.objects.exists())

    def test_admin_reduced_total_has_no_claim_for_difference(self):
        Deposits.register(self.member, 0, True, True, self.today, self.member, {})
        deposit = self.apply(amount="100")
        self.assertEqual(Decimal("100"), deposit.agreed_amount)
        self.assertTrue(deposit.exception_authorized)
        self.assertFalse(deposit.hardship_pending)
        self.assertEqual(
            [Decimal("100")], list(deposit.payments.values_list("amount", flat=True))
        )

    def test_cent_rounding_and_monthly_dates(self):
        deposit = self.apply(amount="100.01", instalments=3, start_date=self.today)
        payments = list(deposit.payments.order_by("due_date"))
        self.assertEqual(
            [Decimal("33.34"), Decimal("33.34"), Decimal("33.33")],
            [p.amount for p in payments],
        )
        self.assertEqual(Decimal("100.01"), sum(p.amount for p in payments))
        self.assertGreaterEqual(payments[0].due_date, self.today)
        self.assertEqual([1, 2, 3], [p.instalment_number for p in payments])
        self.assertEqual(
            [1, 1],
            [
                (b.due_date.year - a.due_date.year) * 12
                + b.due_date.month
                - a.due_date.month
                for a, b in zip(payments, payments[1:])
            ],
        )

    def test_four_rates_of_fifty(self):
        deposit = self.apply(instalments=4)
        self.assertEqual(
            [Decimal("50")] * 4, list(deposit.payments.values_list("amount", flat=True))
        )

    def test_duplicate_request_does_not_duplicate_debit_and_changed_payload_rejected(
        self,
    ):
        key = str(uuid4())
        deposit = self.apply(request_id=key)
        again = self.apply(request_id=key)
        self.assertEqual(deposit.revision, again.revision)
        self.assertEqual(1, deposit.payments.count())
        with self.assertRaises(ValidationError):
            self.apply(request_id=key, amount="250")
        self.assertEqual(1, deposit.operations.count())

    def test_changed_agreement_preserves_exported_history(self):
        deposit = self.apply(instalments=4)
        first = deposit.payments.order_by("due_date").first()
        self.mark_paid(first)
        deposit = self.apply(amount="100", instalments=2)
        first.refresh_from_db()
        self.assertEqual(Decimal("50"), first.amount)
        self.assertIsNotNone(first.transaction_id)
        self.assertEqual(
            [Decimal("25")] * 2,
            list(
                deposit.payments.filter(transaction=None).values_list(
                    "amount", flat=True
                )
            ),
        )
        self.assertEqual(Decimal("50"), Deposits.balances(deposit, {})["received"])

    def test_reduction_below_paid_amount_makes_only_excess_refundable(self):
        deposit = self.apply()
        self.mark_paid(deposit.payments.get())
        deposit = self.apply(amount="100")
        self.assertFalse(deposit.payments.filter(transaction=None).exists())
        self.assertEqual(Decimal("100"), Deposits.balances(deposit, {})["refundable"])
        self.apply(action="refund", amount="100", date=self.today)
        self.assertEqual(Decimal("100"), Deposits.balances(deposit, {})["balance"])
        self.assertEqual(0, Deposits.balances(deposit, {})["refundable"])

    def test_cancellation_removes_only_open_rates_and_external_refund_is_idempotent(
        self,
    ):
        deposit = self.apply(instalments=4)
        paid = deposit.payments.order_by("due_date").first()
        self.mark_paid(paid)
        Deposits.cancel_membership(self.member, self.today, self.admin, {})
        deposit.refresh_from_db()
        self.assertEqual([paid.pk], list(deposit.payments.values_list("pk", flat=True)))
        self.assertEqual(Decimal("50"), Deposits.balances(deposit, {})["refundable"])
        key = str(uuid4())
        self.apply(action="refund", amount="50", date=self.today, request_id=key)
        self.apply(action="refund", amount="50", date=self.today, request_id=key)
        self.assertEqual(1, AssociationDepositBooking.objects.count())
        self.assertEqual(0, Deposits.balances(deposit, {})["balance"])
        with self.assertRaises(ValidationError):
            self.apply(action="refund", amount="0.01", date=self.today)

    def test_future_departure_does_not_make_refund_due_today(self):
        deposit = self.apply()
        self.mark_paid(deposit.payments.get())
        future = self.today + datetime.timedelta(days=60)
        Deposits.cancel_membership(self.member, future, self.admin, {})
        deposit.refresh_from_db()
        self.assertEqual(0, Deposits.balances(deposit, {})["refundable"])
        self.assertEqual(
            Decimal("200"), Deposits.balances(deposit, {}, future)["refundable"]
        )

    def test_external_receipt_reduces_pending_rates_without_new_payment(self):
        deposit = self.apply(instalments=4)
        self.apply(action="receipt", amount="75", date=self.today)
        self.assertEqual(
            [Decimal("25"), Decimal("50"), Decimal("50")],
            list(
                deposit.payments.order_by("due_date").values_list("amount", flat=True)
            ),
        )
        self.assertEqual(Decimal("75"), Deposits.balances(deposit, {})["received"])

    def test_historic_import_is_paid_and_never_debited(self):
        key = "legacy:42"
        deposit = self.apply(
            action="import", amount="200", date=self.today, request_id=key
        )
        self.apply(action="import", amount="200", date=self.today, request_id=key)
        self.assertEqual(Decimal("200"), deposit.agreed_amount)
        self.assertEqual(Decimal("200"), Deposits.balances(deposit, {})["balance"])
        self.assertFalse(deposit.payments.exists())
        self.assertEqual(1, deposit.bookings.count())

    def test_raising_minimum_does_not_create_payment(self):
        deposit = self.apply()
        self.mark_paid(deposit.payments.get())
        self.config["minimum"] = Decimal("300")
        self.assertEqual(Decimal("200"), Deposits.balances(deposit, {})["balance"])
        self.assertFalse(deposit.payments.filter(transaction=None).exists())

    def test_invalid_rate_count_and_past_start_are_atomic(self):
        for kwargs in [
            {"instalments": 0},
            {"instalments": 121},
            {"instalments": 4, "amount": "0.02"},
            {"start_date": self.today - datetime.timedelta(days=1)},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.apply(**kwargs)
        self.assertFalse(AssociationDeposit.objects.exists())

    def test_member_cannot_authorize_reduction_or_read_other_accounts(self):
        self.client.force_login(self.member)
        url = reverse(
            "associations:member_deposit", kwargs={"member_id": self.member.pk}
        )
        response = self.client.post(
            url,
            data={
                "request_id": str(uuid4()),
                "expected_revision": 0,
                "action": "agreement",
                "amount": "100",
                "start_date": str(self.today),
            },
            content_type="application/json",
        )
        self.assertEqual(403, response.status_code)
        other_url = reverse(
            "associations:member_deposit", kwargs={"member_id": self.admin.pk}
        )
        self.assertEqual(403, self.client.get(other_url).status_code)
        self.assertFalse(AssociationDeposit.objects.exists())

    def test_admin_request_retry_and_stale_revision(self):
        self.client.force_login(self.admin)
        url = reverse(
            "associations:member_deposit", kwargs={"member_id": self.member.pk}
        )
        data = {
            "request_id": str(uuid4()),
            "expected_revision": 0,
            "action": "agreement",
            "amount": "100",
            "start_date": str(self.today),
            "note": "Reduzierung genehmigt",
        }
        self.assertEqual(
            200,
            self.client.post(url, data, content_type="application/json").status_code,
        )
        self.assertEqual(
            200,
            self.client.post(url, data, content_type="application/json").status_code,
        )
        data["request_id"] = str(uuid4())
        self.assertEqual(
            400,
            self.client.post(url, data, content_type="application/json").status_code,
        )
        self.assertEqual(1, Payment.objects.count())

    def test_export_failure_leaves_payment_open(self):
        deposit = self.apply()
        payment = deposit.payments.get()
        Payment.objects.filter(pk=payment.pk).update(due_date=self.today)
        with patch(
            "tapir.associations.services.deposit_payment_exporter.Pain008XmlStringGenerator.validate_single_payment",
            side_effect=Pain008XmlSinglePaymentException("IBAN fehlt"),
        ):
            errors = DepositPaymentExporter.export(self.today, False, {})
        self.assertTrue(errors)
        payment.refresh_from_db()
        self.assertIsNone(payment.transaction_id)
        self.assertEqual(Payment.PaymentStatus.DUE, payment.status)

    def test_export_retry_does_not_duplicate_successful_payments(self):
        deposit = self.apply()
        Payment.objects.filter(association_deposit=deposit).update(due_date=self.today)
        with patch(
            "tapir.associations.services.deposit_payment_exporter.Pain008XmlStringGenerator.validate_single_payment"
        ), patch(
            "tapir.associations.services.deposit_payment_exporter.Pain008XmlStringGenerator.build_xml_string",
            return_value=b"<xml/>",
        ), patch(
            "tapir.associations.services.deposit_payment_exporter.export_file",
            side_effect=lambda **kwargs: ExportedFileFactory(),
        ):
            self.assertEqual([], DepositPaymentExporter.export(self.today, False, {}))
            payment = deposit.payments.get()
            self.assertIsNotNone(payment.transaction_id)
            transaction_id = payment.transaction_id
            self.assertEqual([], DepositPaymentExporter.export(self.today, False, {}))
        payment.refresh_from_db()
        self.assertEqual(transaction_id, payment.transaction_id)

    def test_standard_rates_require_configuration_and_cannot_be_combined_with_pending_hardship(
        self,
    ):
        with self.assertRaises(ValidationError):
            Deposits.register(
                self.member,
                200,
                False,
                True,
                self.today,
                self.member,
                {},
                instalments=True,
            )
        self.config["instalments_enabled"] = True
        with self.assertRaises(ValidationError):
            Deposits.register(
                self.member,
                0,
                True,
                True,
                self.today,
                self.member,
                {},
                instalments=True,
            )
        deposit = Deposits.register(
            self.member, 200, False, True, self.today, self.member, {}, instalments=True
        )
        self.assertEqual(4, deposit.payments.count())
        self.assertFalse(deposit.exception_authorized)

    def test_real_xml_partial_failure_and_retry_preserve_successful_history(self):
        from tapir.wirgarten.parameter_keys import ParameterKeys
        from tapir.wirgarten.models import PaymentTransaction
        from xml.etree import ElementTree

        self._set_parameter(
            ParameterKeys.PAYMENT_ORGANISATION_IBAN, "DE60500105172436256838"
        )
        self._set_parameter(
            ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, "DE98ZZZ09999999999"
        )
        first_deposit = self.apply()
        first_payment = first_deposit.payments.get()
        self.member = MemberFactory(iban="DE89370400440532013000")
        second_deposit = self.apply()
        self.member.iban = ""
        self.member.save(update_fields=["iban"])
        Payment.objects.filter(
            association_deposit__in=[first_deposit, second_deposit]
        ).update(due_date=self.today)
        errors = DepositPaymentExporter.export(self.today, False, {})
        self.assertEqual(1, len(errors))
        first_payment.refresh_from_db()
        first_transaction = first_payment.transaction
        self.assertIsNotNone(first_transaction)
        xml_before = bytes(first_transaction.xml_file.file)
        tree = ElementTree.fromstring(xml_before)
        self.assertEqual(
            ["200.00"],
            [node.text for node in tree.iter() if node.tag.endswith("InstdAmt")],
        )
        self.assertIsNone(second_deposit.payments.get().transaction_id)
        self.member.iban = "DE89370400440532013000"
        self.member.save(update_fields=["iban"])
        self.assertEqual([], DepositPaymentExporter.export(self.today, False, {}))
        self.assertEqual([], DepositPaymentExporter.export(self.today, False, {}))
        first_payment.refresh_from_db()
        self.assertEqual(first_transaction.pk, first_payment.transaction_id)
        self.assertEqual(xml_before, bytes(first_payment.transaction.xml_file.file))
        self.assertEqual(2, PaymentTransaction.objects.count())

    def test_file_creation_failure_rolls_back_export_and_sends_no_mail(self):
        from tapir.wirgarten.models import ExportedFile, PaymentTransaction
        from tapir.wirgarten.service.file_export import export_file

        deposit = self.apply()
        deposit.payments.update(due_date=self.today)
        calls = 0

        def failing_export(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("Dateierstellung fehlgeschlagen")
            return export_file(**kwargs)

        with patch(
            "tapir.associations.services.deposit_payment_exporter.Pain008XmlStringGenerator.validate_single_payment"
        ), patch(
            "tapir.associations.services.deposit_payment_exporter.Pain008XmlStringGenerator.build_xml_string",
            return_value=b"<xml/>",
        ), patch(
            "tapir.associations.services.deposit_payment_exporter.export_file",
            side_effect=failing_export,
        ), patch(
            "tapir.associations.services.deposit_payment_exporter.send_exported_file"
        ) as send, self.assertRaises(
            RuntimeError
        ):
            DepositPaymentExporter.export(self.today, True, {})
        self.assertFalse(ExportedFile.objects.exists())
        self.assertFalse(PaymentTransaction.objects.exists())
        self.assertIsNone(deposit.payments.get().transaction_id)
        send.assert_not_called()

    def test_refund_then_later_agreement_accounts_for_refunded_money(self):
        deposit = self.apply()
        self.mark_paid(deposit.payments.get())
        self.apply(amount="100")
        self.apply(action="refund", amount="100", date=self.today)
        deposit = self.apply(amount="200", instalments=2)
        self.assertEqual(
            [Decimal("50")] * 2,
            list(
                deposit.payments.filter(transaction=None).values_list(
                    "amount", flat=True
                )
            ),
        )

    def test_returned_debit_after_refund_can_record_negative_balance_without_automatic_retry(
        self,
    ):
        deposit = self.apply()
        self.mark_paid(deposit.payments.get())
        self.apply(amount="100")
        self.apply(action="refund", amount="100", date=self.today)
        self.apply(action="reversal", amount="200", date=self.today)
        self.assertEqual(Decimal("-100"), Deposits.balances(deposit, {})["balance"])
        self.assertFalse(deposit.payments.filter(transaction=None).exists())

    def test_member_increase_creates_only_delta_and_retries_are_idempotent(self):
        deposit = self.apply()
        initial = deposit.payments.get()
        self.client.force_login(self.member)
        url = reverse(
            "associations:member_deposit", kwargs={"member_id": self.member.pk}
        )
        data = {
            "request_id": str(uuid4()),
            "expected_revision": deposit.revision,
            "action": "increase",
            "amount": "250.00",
        }
        self.assertEqual(
            200,
            self.client.post(url, data, content_type="application/json").status_code,
        )
        self.assertEqual(
            200,
            self.client.post(url, data, content_type="application/json").status_code,
        )
        self.assertEqual(
            Decimal("50"), deposit.payments.exclude(pk=initial.pk).get().amount
        )
        initial.refresh_from_db()
        self.assertEqual(Decimal("200"), initial.amount)
        deposit.refresh_from_db()
        for changes in [
            {"amount": "251"},
            {"amount": "300", "instalments": 2},
            {
                "amount": "300",
                "start_date": str(self.today + datetime.timedelta(days=30)),
            },
        ]:
            with self.subTest(changes=changes):
                request = {
                    **data,
                    "request_id": str(uuid4()),
                    "expected_revision": deposit.revision,
                    **changes,
                }
                self.assertEqual(
                    400,
                    self.client.post(
                        url, request, content_type="application/json"
                    ).status_code,
                )
        self.config["allow_extra_member"] = False
        data.update(
            request_id=str(uuid4()), expected_revision=deposit.revision, amount="300"
        )
        self.assertEqual(
            400,
            self.client.post(url, data, content_type="application/json").status_code,
        )
        self.assertEqual(2, deposit.payments.count())

    def test_optional_supporter_and_signup_extra_configuration(self):
        self.config["supporters_required"] = False
        Deposits.validate_signup(0, False, False, {})
        with self.assertRaises(ValidationError):
            Deposits.validate_signup(0, False, True, {})
        self.config["allow_extra_signup"] = False
        Deposits.validate_signup(200, False, True, {})
        with self.assertRaises(ValidationError):
            Deposits.validate_signup(250, False, True, {})

    def test_membership_type_change_preserves_deposit_and_instalments(self):
        from tapir.associations.services.association_membership_change_handler import (
            AssociationMembershipChangeHandler,
        )
        from tapir.associations.tests.factories import AssociationMembershipTypeFactory

        deposit = self.apply(instalments=4)
        before = list(
            deposit.payments.order_by("id").values("id", "amount", "due_date")
        )
        AssociationMembershipChangeHandler.start_membership(
            member=self.member,
            association_membership_type=AssociationMembershipTypeFactory(),
            start_date=self.today + datetime.timedelta(days=30),
            actor=self.admin,
            cache={},
        )
        deposit.refresh_from_db()
        self.assertIsNone(deposit.cancellation_date)
        self.assertEqual(
            before,
            list(deposit.payments.order_by("id").values("id", "amount", "due_date")),
        )
        self.assertEqual(1, deposit.revision)
        self.assertEqual(Decimal("200"), deposit.agreed_amount)

    def assert_reentry(self, fully_refunded=False, exported=False):
        from tapir.associations.services.association_membership_change_handler import (
            AssociationMembershipChangeHandler,
        )
        from tapir.associations.services.deposit_reporting import DepositReporting
        from tapir.associations.services.deposit_mail_service import DepositMailService
        from tapir.associations.tests.factories import AssociationMembershipTypeFactory
        from tapir.wirgarten.models import Member

        deposit = self.apply(amount="75", instalments=3)
        if exported:
            self.mark_paid(deposit.payments.order_by("due_date").first())
        else:
            self.apply("receipt", "25")
        Deposits.cancel_membership(self.member, self.today, self.admin, {})
        if fully_refunded:
            self.apply("refund", "25")
        reference = datetime.datetime.combine(
            self.today, datetime.time(12), tzinfo=datetime.UTC
        )
        self.assertEqual(
            not fully_refunded, DepositReporting.refundable_members(reference).exists()
        )
        history = list(deposit.bookings.order_by("pk").values())
        exported_history = list(deposit.payments.order_by("pk").values())
        self.assertFalse(deposit.payments.filter(transaction=None).exists())
        membership = AssociationMembershipChangeHandler.start_membership(
            self.member, AssociationMembershipTypeFactory(), self.today, self.admin, {}
        )
        deposit.refresh_from_db()
        self.assertIsNone(deposit.cancellation_date)
        self.assertIsNone(deposit.agreed_amount)
        self.assertFalse(deposit.hardship_pending)
        self.assertFalse(deposit.exception_authorized)
        self.assertFalse(DepositReporting.refundable_members(reference).exists())
        self.assertEqual(history, list(deposit.bookings.order_by("pk").values()))
        self.assertEqual(
            exported_history, list(deposit.payments.order_by("pk").values())
        )
        balances = Deposits.balances(deposit, {})
        self.assertEqual(0 if fully_refunded else 25, balances["balance"])
        self.assertEqual(0, balances["refundable"])
        self.assertEqual(0, balances["pending"])
        annotated = DepositReporting.annotate_members(
            Member.objects.filter(pk=self.member.pk), {}
        ).get()
        self.assertEqual(0, annotated.deposit_refundable)
        self.assertEqual(
            "Individuelle Vereinbarung offen", DepositReporting.status(annotated)
        )
        self.assertEqual(
            "Individuelle Vereinbarung offen",
            DepositMailService.amount_token(self.member, {}),
        )
        self.assertEqual(
            [self.member.pk],
            list(
                DepositReporting.filter_members(
                    Member.objects.all(), "pending", {}
                ).values_list("pk", flat=True)
            ),
        )
        self.assertFalse(
            DepositReporting.filter_members(Member.objects.all(), "exempt", {}).exists()
        )
        self.assertEqual(1, DepositReporting.dashboard({})["pending_cases"])
        self.assertEqual([], DepositReporting.dashboard({})["cohorts"])
        operation = deposit.operations.get(
            request_id=f"membership-rejoin:{membership.pk}"
        )
        self.assertEqual("75.00", operation.changes["before"]["agreed_amount"])
        self.assertEqual(
            str(self.today), operation.changes["before"]["cancellation_date"]
        )
        self.assertIsNone(operation.changes["after"]["agreed_amount"])
        self.assertTrue(
            AssociationDepositLogEntry.objects.filter(operation=operation).exists()
        )

        self.client.force_login(self.member)
        url = reverse(
            "associations:member_deposit", kwargs={"member_id": self.member.pk}
        )
        details = self.client.get(url).json()
        self.assertIsNone(details["agreed_amount"])
        self.assertIsNone(details["cancellation_date"])
        self.assertFalse(details["can_increase"])
        self.assertEqual("0.00", details["refundable"])
        with self.assertRaises(ValidationError):
            self.apply("refund", "25")
        with self.assertRaises(ValidationError):
            self.apply("increase", "200")

        self.client.force_login(self.admin)
        data = {
            "request_id": str(uuid4()),
            "expected_revision": deposit.revision,
            "action": "agreement",
            "amount": "75",
            "instalments": 3 if fully_refunded else 2,
            "start_date": str(self.today),
            "note": "Neue Zustimmung zum Wiedereintritt dokumentiert",
        }
        for _ in range(2):
            response = self.client.post(url, data, content_type="application/json")
            self.assertEqual(200, response.status_code, response.content)
        open_payments = list(
            deposit.payments.filter(transaction=None)
            .order_by("due_date")
            .values("id", "amount", "due_date")
        )
        self.assertEqual(
            [Decimal("25")] * (3 if fully_refunded else 2),
            [p["amount"] for p in open_payments],
        )
        self.assertEqual(0, DepositReporting.dashboard({})["pending_cases"])
        # Retrying the lifecycle hook or changing the membership type keeps the new agreement.
        Deposits.rejoin_membership(membership, self.admin, {})
        AssociationMembershipChangeHandler.start_membership(
            self.member, AssociationMembershipTypeFactory(), self.today, self.admin, {}
        )
        deposit.refresh_from_db()
        self.assertEqual(Decimal("75"), deposit.agreed_amount)
        self.assertEqual(
            open_payments,
            list(
                deposit.payments.filter(transaction=None)
                .order_by("due_date")
                .values("id", "amount", "due_date")
            ),
        )

    def test_reentry_preserves_credit_and_requires_new_agreement(self):
        self.assert_reentry()

    def test_reentry_after_full_refund_preserves_history_and_requires_new_agreement(
        self,
    ):
        self.assert_reentry(fully_refunded=True)

    def test_reentry_preserves_exported_payment_history(self):
        self.assert_reentry(exported=True)

    def test_type_change_before_scheduled_exit_does_not_reopen_deposit(self):
        from tapir.associations.services.association_membership_change_handler import (
            AssociationMembershipChangeHandler,
        )
        from tapir.associations.tests.factories import AssociationMembershipTypeFactory

        deposit = self.apply()
        exit_date = self.today + datetime.timedelta(days=60)
        Deposits.cancel_membership(self.member, exit_date, self.admin, {})
        AssociationMembershipChangeHandler.start_membership(
            self.member, AssociationMembershipTypeFactory(), self.today, self.admin, {}
        )
        deposit.refresh_from_db()
        self.assertEqual(exit_date, deposit.cancellation_date)
        self.assertEqual(Decimal("200"), deposit.agreed_amount)
        self.assertEqual(2, deposit.revision)
