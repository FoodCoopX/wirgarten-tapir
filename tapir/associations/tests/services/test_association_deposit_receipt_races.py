import datetime
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.core.cache import cache
from django.db import close_old_connections
from django.test import TransactionTestCase

from tapir.associations.models import (
    AssociationDepositReceipt,
    AssociationDepositReceiptCreatedLogEntry,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import (
    TapirFactoryMixin,
    mock_keycloak,
    mock_timezone,
)


class TestAssociationDepositReceiptRaces(TapirFactoryMixin, TransactionTestCase):
    # Separate connections need committed fixtures, outside TestCase's transaction.
    def setUp(self):
        super().setUp()
        self.factory_setup()
        cache.clear()
        mock_keycloak(self)
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_ASSOCIATION)
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.first = MemberFactory()
        self.second = MemberFactory()

    def test_members_can_record_receipts_for_each_other_concurrently(self):
        barrier = Barrier(2)
        original_create = AssociationDepositReceipt.objects.create

        def create_then_wait(**kwargs):
            receipt = original_create(**kwargs)
            barrier.wait(timeout=10)
            return receipt

        def record(member_id, actor_id):
            close_old_connections()
            try:
                return AssociationDepositReceiptRecorder.record_received_deposit(
                    member=Member.objects.get(pk=member_id),
                    actor=Member.objects.get(pk=actor_id),
                    amount=Decimal("25"),
                    received_on=datetime.date(2026, 11, 5),
                    reference=f"receipt-{member_id}",
                    note="Kontoauszug",
                    cache={},
                ).pk
            finally:
                close_old_connections()

        with patch.object(
            AssociationDepositReceipt.objects, "create", side_effect=create_then_wait
        ), ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(record, self.first.pk, self.second.pk)
            second = pool.submit(record, self.second.pk, self.first.pk)
            self.assertNotEqual(first.result(timeout=20), second.result(timeout=20))

        self.assertEqual(2, AssociationDepositReceipt.objects.count())
        self.assertEqual(
            {(self.first.pk, self.second.pk), (self.second.pk, self.first.pk)},
            set(
                AssociationDepositReceiptCreatedLogEntry.objects.values_list(
                    "user_id", "actor_id"
                )
            ),
        )
