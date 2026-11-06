import datetime
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.test import TransactionTestCase
from django.db import close_old_connections, connection

from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_increase_preview import (
    AssociationDepositIncreasePreview,
)
from tapir.associations.services.association_deposit_increase_recorder import (
    AssociationDepositIncreaseRecorder,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.models import Member, ExportedFile
from tapir.wirgarten.tests.test_utils import (
    TapirFactoryMixin,
    mock_keycloak,
    mock_timezone,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.associations.tests.factories import (
    AssociationMembershipFactory,
    AssociationDepositAccountFactory,
)


class TestAssociationDepositLifecycleRaces(TapirFactoryMixin, TransactionTestCase):
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

    def run_lifecycle_race(self, first, second):
        barrier = Barrier(2)

        def worker(action):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                member = Member.objects.get(pk=self.member.pk)
                barrier.wait(timeout=10)
                return action(member)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, action) for action in [first, second]]
            return [future.result(timeout=20) for future in futures]

    def prepare_lifecycle_payment(self):
        AssociationMembership.objects.filter(member=self.member).update(
            start_date=datetime.date(2026, 10, 1)
        )
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )

    def end_membership(self, member):
        AssociationMembershipChangeHandler.set_end_date(
            AssociationMembership.objects.get(member=member),
            datetime.date(2026, 11, 4),
            member,
            {},
        )

    def test_exit_racing_real_export_preserves_committed_rows_or_prevents_collection(
        self,
    ):
        self.prepare_lifecycle_payment()
        self.run_lifecycle_race(
            self.end_membership,
            lambda member: PaymentExportBuilder.export_all_unexported_payments(
                datetime.date(2026, 11, 5), False, {}
            ),
        )
        before = list(self.account.payments.values())
        files = list(ExportedFile.objects.order_by("pk").values())
        file_ids = [row["id"] for row in files]
        PaymentExportBuilder.export_all_unexported_payments(
            datetime.date(2026, 11, 5), False, {}
        )
        self.assertEqual(before, list(self.account.payments.values()))
        self.assertEqual(
            files,
            list(ExportedFile.objects.filter(pk__in=file_ids).order_by("pk").values()),
        )
        self.assertEqual(
            0,
            AssociationDepositDetailsProvider.get_deposit_details(self.member, {})[
                "pending_amount"
            ],
        )

    def test_exit_racing_receipt_preserves_credit_without_new_debit(self):
        self.prepare_lifecycle_payment()
        self.run_lifecycle_race(
            self.end_membership,
            lambda member: AssociationDepositReceiptRecorder.record_received_deposit(
                member,
                Decimal("25"),
                datetime.date(2026, 11, 5),
                "lifecycle-race-receipt",
                "Kontoauszug",
                member,
                {},
            ),
        )
        self.assertEqual(1, self.account.receipts.count())
        self.assertEqual(Decimal("175"), self.account.payments.get().amount)
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertEqual(25, details["received_amount"])
        self.assertEqual(0, details["pending_amount"])
        self.assertEqual(175, details["stopped_amount"])

    def test_exit_racing_signed_increase_serializes_or_rejects_stale_terms(self):
        self.prepare_lifecycle_payment()
        TapirParameter.objects.filter(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE
        ).update(value="True")
        preview = AssociationDepositIncreasePreview.build_preview(
            self.member, Decimal("250"), {}
        )

        def increase(member):
            try:
                AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                    member,
                    Decimal("250"),
                    member,
                    {},
                    confirmation=preview["confirmation"],
                )
                return "applied"
            except ValidationError:
                return "stale"

        _, result = self.run_lifecycle_race(self.end_membership, increase)
        self.account.refresh_from_db()
        self.assertEqual(
            Decimal("250") if result == "applied" else Decimal("200"),
            self.account.agreed_amount,
        )
        self.assertEqual(
            0,
            AssociationDepositDetailsProvider.get_deposit_details(self.member, {})[
                "pending_amount"
            ],
        )

    def test_reentry_racing_real_export_does_not_collect_old_plan(self):
        self.prepare_lifecycle_payment()
        self.end_membership(self.member)
        kind = AssociationMembership.objects.get(member=self.member).type
        self.run_lifecycle_race(
            lambda member: AssociationMembershipChangeHandler.start_membership(
                member, kind, datetime.date(2026, 11, 6), member, {}
            ),
            lambda member: PaymentExportBuilder.export_all_unexported_payments(
                datetime.date(2026, 12, 5), False, {}
            ),
        )
        self.assertFalse(
            self.account.payments.filter(transaction__isnull=False).exists()
        )
        self.assertEqual(
            "agreement_required",
            AssociationDepositDetailsProvider.get_deposit_details(self.member, {})[
                "state"
            ],
        )
