from django.utils import timezone

from tapir.subscriptions.views.confirmations import MemberDataToConfirmApiView
from tapir.wirgarten.models import SubscriptionChangeLogEntry, CoopShareTransaction
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    CoopShareTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetNumberOfUnconfirmedChanges(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getNumberOfUnconfirmedChanges_noChanges_returnsZero(self):
        SubscriptionFactory.create(cancellation_ts=None, admin_confirmed=timezone.now())

        self.assertEqual(
            0, MemberDataToConfirmApiView.get_number_of_unconfirmed_changes()
        )

    def test_getNumberOfUnconfirmedChanges_default_countsEachMemberWithChangesOnce(
        self,
    ):
        cancellation = SubscriptionFactory.create(
            cancellation_ts=timezone.now(), cancellation_admin_confirmed=None
        )
        SubscriptionFactory.create(
            member=cancellation.member, cancellation_ts=None, admin_confirmed=None
        )
        SubscriptionFactory.create(cancellation_ts=None, admin_confirmed=None)
        SubscriptionChangeLogEntry.objects.create(
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
            subscriptions="test",
            admin_confirmed=None,
            user=MemberFactory.create(),
        )
        CoopShareTransactionFactory.create(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            admin_confirmed=None,
            member=cancellation.member,
        )
        CoopShareTransactionFactory.create(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            admin_confirmed=None,
        )
        SubscriptionFactory.create(
            cancellation_ts=timezone.now(), cancellation_admin_confirmed=timezone.now()
        )

        result = MemberDataToConfirmApiView.get_number_of_unconfirmed_changes()

        self.assertEqual(4, result)
        self.assertEqual(
            len(MemberDataToConfirmApiView.build_changes_by_member(cache={})), result
        )
