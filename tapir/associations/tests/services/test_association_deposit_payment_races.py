import datetime
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import close_old_connections, transaction
from django.test import TransactionTestCase
from lxml import etree

from tapir.associations.services.association_deposit_increase_preview import (
    AssociationDepositIncreasePreview,
)
from tapir.associations.services.association_deposit_signup_handler import (
    AssociationDepositSignupHandler,
)
from tapir.associations.services.association_deposit_increase_recorder import (
    AssociationDepositIncreaseRecorder,
)
from tapir.associations.services.association_deposit_agreement_authorizer import (
    AssociationDepositAgreementAuthorizer,
)
from tapir.associations.models import (
    AssociationDepositAgreementAuthorizedLogEntry,
    AssociationDepositAccount,
    AssociationDepositPaymentCreatedLogEntry,
    AssociationDepositReceipt,
    AssociationDepositIncreasedLogEntry,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.tests.factories import (
    AssociationDepositAccountFactory,
    AssociationMembershipFactory,
)
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.models import (
    Member,
    Payment,
    MandateReference,
    PaymentTransaction,
    ExportedFile,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
from tapir.wirgarten.tests.test_utils import (
    TapirFactoryMixin,
    mock_keycloak,
    mock_timezone,
)


class TestAssociationDepositPaymentRaces(TapirFactoryMixin, TransactionTestCase):
    # Worker connections need committed fixtures; TestCase's outer transaction would hide them.
    def setUp(self):
        super().setUp()
        self.factory_setup()
        cache.clear()
        mock_keycloak(self)
        configure_mail_module()
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED
        ).update(value="True")
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_ASSOCIATION)
        TapirParameter.objects.filter(
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN
        ).update(value="NL88ABNA2011060885")
        TapirParameter.objects.filter(
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER
        ).update(value="DE98ZZZ09999999999")
        TapirParameter.objects.filter(
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM
        ).update(value="False")
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.member = MemberFactory(
            iban="NL88ABNA2011060885", account_owner="Kontoinhaber"
        )
        AssociationMembershipFactory(
            member=self.member, start_date=datetime.date(2026, 11, 5), end_date=None
        )
        self.account = AssociationDepositAccountFactory(
            member=self.member,
            agreed_amount=Decimal("200"),
            effective_from=datetime.date(2026, 11, 5),
        )

    def run_requests(self, actions):
        barrier = Barrier(len(actions))

        def worker(action):
            close_old_connections()
            try:
                member = Member.objects.get(pk=self.member.pk)
                barrier.wait(timeout=10)
                if action.startswith("agreement"):
                    try:
                        return (
                            AssociationDepositAgreementAuthorizer.authorize_agreement(
                                member,
                                Decimal("100"),
                                datetime.date(2026, 11, 5),
                                4,
                                datetime.date(2026, 11, 5),
                                "Dokumentierte Zustimmung",
                                0,
                                self.agreement_keys[action],
                                self.agreement_admin,
                                {},
                            ).pk
                        )
                    except ValidationError as error:
                        if "inzwischen" in str(error):
                            return "stale"
                        raise
                if action.startswith("confirmed_increase"):
                    try:
                        return (
                            AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                                member,
                                self.increase_requests[action][0],
                                member,
                                {},
                                confirmation=self.increase_requests[action][1],
                            ).pk
                        )
                    except ValidationError as error:
                        if "inzwischen" in str(error) or "nur erhöht" in str(error):
                            return "stale"
                        raise
                if action == "payment":
                    return AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
                        member, member, {}
                    ).pk
                if action == "increase":
                    return AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                        member, Decimal("250"), member, {}
                    ).pk
                if action == "export":
                    return PaymentExportBuilder.export_all_unexported_payments(
                        datetime.date(2026, 11, 5), False, {}
                    )
                try:
                    return AssociationDepositReceiptRecorder.record_received_deposit(
                        member,
                        Decimal("25"),
                        datetime.date(2026, 11, 5),
                        "concurrent-receipt",
                        "Kontoauszug",
                        member,
                        {},
                        expected_committed_amount=(
                            Decimal("0") if action == "confirmed_receipt" else None
                        ),
                    ).pk
                except ValidationError as error:
                    if action == "confirmed_receipt" and "Seit dem Öffnen" in str(
                        error
                    ):
                        return "stale"
                    raise
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            results = [pool.submit(worker, action) for action in actions]
            return [result.result(timeout=20) for result in results]

    def test_concurrent_payment_requests_create_one_payment_mandate_and_audit(self):
        ids = self.run_requests(["payment", "payment"])
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(1, Payment.objects.count())
        self.assertEqual(1, MandateReference.objects.count())
        self.assertEqual(1, AssociationDepositPaymentCreatedLogEntry.objects.count())

    def test_receipt_racing_with_payment_creation_leaves_only_remaining_amount(self):
        self.run_requests(["payment", "receipt"])
        self.assertEqual(Decimal("175"), self.account.payments.get().amount)
        self.assertEqual(1, self.account.receipts.count())

    def test_concurrent_receipt_retries_reduce_existing_payment_only_once(self):
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )
        ids = self.run_requests(["receipt", "receipt"])
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(1, self.account.receipts.count())
        self.assertEqual(Decimal("175"), self.account.payments.get().amount)

    def test_concurrent_exports_create_only_one_bank_file_pair(self):
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )
        self.run_requests(["export", "export"])
        self.assertEqual(
            1,
            PaymentTransaction.objects.filter(
                type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT
            ).count(),
        )
        transaction = PaymentTransaction.objects.get(
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT
        )
        self.assertEqual(
            2,
            ExportedFile.objects.filter(
                pk__in=[transaction.csv_file_id, transaction.xml_file_id]
            ).count(),
        )
        self.assertEqual(Payment.PaymentStatus.PAID, self.account.payments.get().status)

    def test_receipt_racing_with_export_preserves_committed_file_and_credit(self):
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )
        self.run_requests(["export", "receipt"])
        payment = self.account.payments.get()
        self.assertIn(payment.amount, [Decimal("175"), Decimal("200")])
        self.assertEqual(Decimal("25"), self.account.receipts.get().amount)
        before = list(self.account.payments.values())
        files = list(ExportedFile.objects.order_by("pk").values())
        self.assertIsNone(
            AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
                self.member, self.member, {}
            )
        )
        PaymentExportBuilder.export_all_unexported_payments(
            datetime.date(2026, 11, 5), False, {}
        )
        self.assertEqual(before, list(self.account.payments.values()))
        self.assertEqual(files, list(ExportedFile.objects.order_by("pk").values()))

    def test_concurrent_mixed_exports_collect_contract_and_deposit_only_once(self):
        deposit = AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )
        contract = PaymentFactory(
            mandate_ref=deposit.mandate_ref,
            amount=25,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
            due_date=datetime.date(2026, 11, 5),
            type="Vereinsbeitrag",
            subscription_payment_range_start=datetime.date(2026, 11, 1),
            subscription_payment_range_end=datetime.date(2026, 11, 30),
        )
        self.run_requests(["export", "export"])
        self.assertEqual(1, PaymentTransaction.objects.filter(type="Verträge").count())
        self.assertEqual(
            1,
            PaymentTransaction.objects.filter(
                type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT
            ).count(),
        )
        contract.refresh_from_db()
        deposit.refresh_from_db()
        self.assertEqual(Decimal("25"), contract.amount)
        self.assertEqual(Decimal("200"), deposit.amount)
        self.assertIsNotNone(contract.transaction_id)
        self.assertIsNotNone(deposit.transaction_id)
        self.assertNotEqual(contract.transaction_id, deposit.transaction_id)
        for payment, amount in [(contract, "25.00"), (deposit, "200.00")]:
            xml = etree.fromstring(bytes(payment.transaction.xml_file.file))
            self.assertEqual(
                [amount],
                xml.xpath(
                    "//p:InstdAmt/text()",
                    namespaces={"p": "urn:iso:std:iso:20022:tech:xsd:pain.008.001.08"},
                ),
            )

    def test_members_can_create_payments_for_each_other_concurrently(self):
        other = MemberFactory(iban="NL88ABNA2011060885", account_owner="Kontoinhaber")
        AssociationMembershipFactory(
            member=other, start_date=datetime.date(2026, 11, 5), end_date=None
        )
        AssociationDepositAccountFactory(
            member=other,
            agreed_amount=Decimal("200"),
            effective_from=datetime.date(2026, 11, 5),
        )
        barrier = Barrier(2)
        original_create = Payment.objects.create

        def create_then_wait(**kwargs):
            payment = original_create(**kwargs)
            barrier.wait(timeout=10)
            return payment

        def create(member_id, actor_id):
            close_old_connections()
            try:
                return AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
                    Member.objects.get(pk=member_id),
                    Member.objects.get(pk=actor_id),
                    {},
                ).pk
            finally:
                close_old_connections()

        with patch.object(
            Payment.objects, "create", side_effect=create_then_wait
        ), ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(create, self.member.pk, other.pk)
            second = pool.submit(create, other.pk, self.member.pk)
            self.assertNotEqual(first.result(timeout=20), second.result(timeout=20))

        self.assertEqual(2, Payment.objects.count())
        self.assertEqual(2, MandateReference.objects.count())
        self.assertEqual(
            {(self.member.pk, other.pk), (other.pk, self.member.pk)},
            set(
                AssociationDepositPaymentCreatedLogEntry.objects.values_list(
                    "user_id", "actor_id"
                )
            ),
        )

    def test_export_member_lock_allows_receipt_audit_for_another_member(self):
        other = MemberFactory()
        payment = AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )

        def record():
            close_old_connections()
            try:
                return AssociationDepositReceiptRecorder.record_received_deposit(
                    member=Member.objects.get(pk=other.pk),
                    actor=Member.objects.get(pk=self.member.pk),
                    amount=Decimal("25"),
                    received_on=datetime.date(2026, 11, 5),
                    reference="receipt-during-export",
                    note="Kontoauszug",
                    cache={},
                ).pk
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                payments = AssociationDepositPaymentSynchronizer.prepare_due_payments_for_export(
                    payment.due_date, {}
                )
                self.assertEqual(1, len(payments))
                receipt_id = pool.submit(record).result(timeout=5)
        self.assertEqual(
            receipt_id, AssociationDepositReceipt.objects.get(account__member=other).pk
        )

    def enable_member_increases(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE
        ).update(value="True")
        AssociationMembershipFactory(
            member=self.member, start_date=datetime.date(2026, 11, 5), end_date=None
        )

    def test_concurrent_identical_increases_change_agreement_and_debit_once(self):
        self.enable_member_increases()
        self.run_requests(["increase", "increase"])
        self.account.refresh_from_db()
        self.assertEqual(Decimal("250"), self.account.agreed_amount)
        self.assertEqual(1, AssociationDepositIncreasedLogEntry.objects.count())
        self.assertEqual(Decimal("250"), self.account.payments.get().amount)
        self.assertEqual(1, MandateReference.objects.count())

    def test_increase_racing_with_receipt_keeps_correct_remaining_debit(self):
        self.enable_member_increases()
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )
        self.run_requests(["increase", "receipt"])
        self.account.refresh_from_db()
        self.assertEqual(Decimal("250"), self.account.agreed_amount)
        self.assertEqual(Decimal("25"), self.account.receipts.get().amount)
        self.assertEqual(Decimal("225"), self.account.payments.get().amount)

    def test_concurrent_admin_retries_create_one_agreement_and_four_rates(self):
        self.agreement_admin = MemberFactory(is_superuser=True)
        self.agreement_keys = {"agreement": uuid.uuid4()}
        results = self.run_requests(["agreement", "agreement"])
        self.assertEqual(results[0], results[1])
        self.assertEqual(
            1, AssociationDepositAgreementAuthorizedLogEntry.objects.count()
        )
        self.assertEqual(
            [Decimal("25")] * 4,
            list(self.account.payments.values_list("amount", flat=True)),
        )

    def test_concurrent_different_admin_requests_reject_the_stale_revision(self):
        self.agreement_admin = MemberFactory(is_superuser=True)
        self.agreement_keys = {
            "agreement_one": uuid.uuid4(),
            "agreement_two": uuid.uuid4(),
        }
        results = self.run_requests(["agreement_one", "agreement_two"])
        self.assertEqual(1, results.count("stale"))
        self.assertEqual(
            1, AssociationDepositAgreementAuthorizedLogEntry.objects.count()
        )
        self.assertEqual(4, self.account.payments.count())
        self.account.refresh_from_db()
        self.assertEqual(1, self.account.agreement_revision)

    def test_confirmed_receipt_racing_export_requires_reconfirmation_if_export_wins(
        self,
    ):
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )
        results = self.run_requests(["export", "confirmed_receipt"])
        payment = self.account.payments.get()
        self.assertIsNotNone(payment.transaction_id)
        if results[1] == "stale":
            self.assertFalse(self.account.receipts.exists())
            self.assertEqual(Decimal("200"), payment.amount)
        else:
            self.assertEqual(1, self.account.receipts.count())
            self.assertEqual(Decimal("175"), payment.amount)

    def prepare_confirmed_standard_increases(self):
        self._set_race_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True
        )
        self._set_race_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        self.account.delete()
        AssociationDepositSignupHandler.create_signup_deposit(
            self.member,
            Decimal("200"),
            datetime.date(2026, 11, 5),
            True,
            self.member,
            {},
            payment_option="standard_instalments",
            expected_instalments=4,
        )
        self.account = AssociationDepositAccount.objects.get(member=self.member)
        self.increase_requests = {}
        for amount in [Decimal("250"), Decimal("300")]:
            preview = AssociationDepositIncreasePreview.build_preview(
                self.member, amount, {}
            )
            self.increase_requests["confirmed_increase_" + str(amount)] = (
                amount,
                preview["confirmation"],
            )

    @staticmethod
    def _set_race_parameter(key, value):
        TapirParameter.objects.filter(key=key).update(value=str(value))

    def test_concurrent_identical_confirmed_increases_create_one_standard_increase(
        self,
    ):
        self.prepare_confirmed_standard_increases()
        results = self.run_requests(
            ["confirmed_increase_250", "confirmed_increase_250"]
        )
        self.assertEqual(results[0], results[1])
        self.assertEqual(
            [Decimal("62.50")] * 4,
            list(self.account.payments.values_list("amount", flat=True)),
        )
        self.assertEqual(1, AssociationDepositIncreasedLogEntry.objects.count())

    def test_competing_confirmed_targets_require_reconfirmation_for_second_writer(self):
        self.prepare_confirmed_standard_increases()
        results = self.run_requests(
            ["confirmed_increase_250", "confirmed_increase_300"]
        )
        self.assertEqual(1, results.count("stale"))
        self.account.refresh_from_db()
        self.assertEqual(
            self.account.agreed_amount,
            sum(self.account.payments.values_list("amount", flat=True)),
        )
        self.assertEqual(1, AssociationDepositIncreasedLogEntry.objects.count())

    def test_receipt_racing_confirmed_standard_increase_is_included_or_rejected_as_stale(
        self,
    ):
        self.prepare_confirmed_standard_increases()
        results = self.run_requests(["confirmed_increase_250", "receipt"])
        self.account.refresh_from_db()
        self.assertEqual(1, self.account.receipts.count())
        expected = Decimal("200") if results[0] == "stale" else Decimal("250")
        self.assertEqual(expected, self.account.agreed_amount)
        self.assertEqual(
            expected - 25, sum(self.account.payments.values_list("amount", flat=True))
        )
