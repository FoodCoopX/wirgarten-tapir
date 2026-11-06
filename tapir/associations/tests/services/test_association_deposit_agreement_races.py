import datetime
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.core.cache import cache
from django.db import close_old_connections
from django.test import TransactionTestCase

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementCreatedLogEntry,
)
from tapir.associations.services.association_deposit_agreement_creator import (
    AssociationDepositAgreementCreator,
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


class TestAssociationDepositAgreementRaces(TapirFactoryMixin, TransactionTestCase):
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

    def test_members_can_agree_deposits_for_each_other_concurrently(self):
        barrier = Barrier(2)
        original_save = AssociationDepositAccount.save

        def save_then_wait(account, *args, **kwargs):
            result = original_save(account, *args, **kwargs)
            if account.agreed_amount is not None:
                barrier.wait(timeout=10)
            return result

        def agree(member_id, actor_id):
            close_old_connections()
            try:
                return AssociationDepositAgreementCreator.create_regular_agreement(
                    member=Member.objects.get(pk=member_id),
                    actor=Member.objects.get(pk=actor_id),
                    amount=Decimal("200"),
                    effective_from=datetime.date(2026, 11, 5),
                    cache={},
                ).pk
            finally:
                close_old_connections()

        with patch.object(
            AssociationDepositAccount, "save", new=save_then_wait
        ), ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(agree, self.first.pk, self.second.pk)
            second = pool.submit(agree, self.second.pk, self.first.pk)
            self.assertNotEqual(first.result(timeout=20), second.result(timeout=20))

        self.assertEqual(
            2, AssociationDepositAccount.objects.filter(agreed_amount=200).count()
        )
        self.assertEqual(
            {(self.first.pk, self.second.pk), (self.second.pk, self.first.pk)},
            set(
                AssociationDepositAgreementCreatedLogEntry.objects.values_list(
                    "user_id", "actor_id"
                )
            ),
        )
