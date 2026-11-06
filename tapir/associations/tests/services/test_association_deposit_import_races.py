import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.core.cache import cache
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositImportedLogEntry,
    AssociationDepositReceipt,
)
from tapir.associations.services.association_deposit_importer import (
    AssociationDepositImporter,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.wirgarten.models import Payment, PaymentTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import (
    TapirFactoryMixin,
    mock_keycloak,
    mock_timezone,
)


class TestAssociationDepositImportRaces(TapirFactoryMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.factory_setup()
        cache.clear()
        mock_keycloak(self)
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        configure_mail_module()
        ParameterDefinitions().import_definitions(bulk_create=True)
        for key, value in {
            ParameterKeys.ORGANISATION_LEGAL_STATUS: LEGAL_STATUS_ASSOCIATION,
            ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED: True,
            ParameterKeys.PAYMENT_DUE_DAY: 5,
            ParameterKeys.PAYMENT_ORGANISATION_IBAN: "NL88ABNA2011060885",
            ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER: "DE98ZZZ09999999999",
            ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM: False,
        }.items():
            TapirParameter.objects.filter(key=key).update(value=str(value))
        self.member = MemberFactory(
            iban="NL88ABNA2011060885",
            account_owner="Test Mitglied",
            sepa_consent=datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc),
        )
        AssociationMembershipFactory(
            member=self.member, start_date=datetime.date(2026, 1, 1)
        )
        self.row = {
            "Nr": str(self.member.member_no),
            "Einlage Status": "vereinbart",
            "Einlage Gesamt": "200",
            "Einlage Erhalten": "100",
            "Einlage Stichtag": "2026-11-05",
            "Einlage Beginn": "2026-09-01",
            "Einlage Ratenzahl": "4",
            "Einlage Offene Raten": "2026-11-20:50|2026-12-20:50",
            "Einlage Beleg": "Historischer Stand",
        }

    def run_concurrently(self, *operations):
        barrier = Barrier(len(operations))

        def worker(operation):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                barrier.wait(timeout=10)
                return operation()
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return [
                future.result(timeout=20)
                for future in [
                    pool.submit(worker, operation) for operation in operations
                ]
            ]

    def test_two_connections_import_same_snapshot_only_once(self):
        results = self.run_concurrently(
            lambda: AssociationDepositImporter.import_deposit(self.row, {}),
            lambda: AssociationDepositImporter.import_deposit(self.row, {}),
        )
        self.assertCountEqual(
            [MEMBER_IMPORT_STATUS_CREATED, MEMBER_IMPORT_STATUS_SKIPPED], results
        )
        self.assertEqual(1, AssociationDepositAccount.objects.count())
        self.assertEqual(1, AssociationDepositReceipt.objects.count())
        self.assertEqual(1, AssociationDepositImportedLogEntry.objects.count())
        self.assertEqual(2, Payment.objects.count())
        self.assertEqual(
            [50, 50], list(Payment.objects.values_list("amount", flat=True))
        )

    def test_repeated_import_against_export_never_collects_future_rates_early(self):
        AssociationDepositImporter.import_deposit(self.row, {})
        before = list(Payment.objects.order_by("pk").values())
        self.run_concurrently(
            lambda: AssociationDepositImporter.import_deposit(self.row, {}),
            lambda: PaymentExportBuilder.export_association_deposit_payments(
                datetime.date(2026, 11, 5), False, {}
            ),
        )
        self.assertEqual(before, list(Payment.objects.order_by("pk").values()))
        self.assertFalse(PaymentTransaction.objects.exists())
        self.assertEqual(1, AssociationDepositImportedLogEntry.objects.count())

    def test_repeat_against_due_export_preserves_one_paid_row_and_original_schedule(
        self,
    ):
        AssociationDepositImporter.import_deposit(self.row, {})
        mock_timezone(self, datetime.datetime(2026, 11, 20, 12))
        results = self.run_concurrently(
            lambda: AssociationDepositImporter.import_deposit(self.row, {}),
            lambda: PaymentExportBuilder.export_association_deposit_payments(
                datetime.date(2026, 11, 20), False, {}
            ),
        )
        self.assertIn(MEMBER_IMPORT_STATUS_SKIPPED, results)
        self.assertEqual(1, PaymentTransaction.objects.count())
        self.assertEqual(
            1, Payment.objects.filter(status=Payment.PaymentStatus.PAID).count()
        )
        self.assertEqual(
            1, Payment.objects.filter(status=Payment.PaymentStatus.DUE).count()
        )
        self.assertEqual(
            [datetime.date(2026, 12, 5), datetime.date(2026, 12, 20)],
            list(
                Payment.objects.order_by("due_date").values_list("due_date", flat=True)
            ),
        )
        self.assertEqual(1, AssociationDepositImportedLogEntry.objects.count())
