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


class TestBuildChangesByMember(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_buildChangesByMember_subscriptionNotCancelled_subscriptionNotAddedToCancellations(
        self,
    ):
        subscription = SubscriptionFactory.create(
            cancellation_ts=None, cancellation_admin_confirmed=None
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertEqual(
            result[subscription.member][subscription.product.type]["cancellations"], []
        )

    def test_buildChangesByMember_subscriptionCancelledButNotConfirmed_subscriptionAddedToCancellations(
        self,
    ):
        subscription = SubscriptionFactory.create(
            cancellation_ts=timezone.now(), cancellation_admin_confirmed=None
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertEqual(
            result[subscription.member][subscription.product.type]["cancellations"],
            [subscription],
        )

    def test_buildChangesByMember_subscriptionCancelledAndConfirmed_subscriptionNotAddedToCancellations(
        self,
    ):
        subscription = SubscriptionFactory.create(
            cancellation_ts=timezone.now(), cancellation_admin_confirmed=timezone.now()
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertNotIn(subscription.member, result.keys())

    def test_buildChangesByMember_subscriptionCancelledAndCreationNotConfirmed_subscriptionAddedToCancellationsButNotToCreations(
        self,
    ):
        subscription = SubscriptionFactory.create(
            cancellation_ts=timezone.now(),
            cancellation_admin_confirmed=None,
            admin_confirmed=None,
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertEqual(
            result[subscription.member][subscription.product.type]["cancellations"],
            [subscription],
        )
        self.assertEqual(
            result[subscription.member][subscription.product.type]["creations"],
            [],
        )

    def test_buildChangesByMember_subscriptionCreationNotConfirmed_subscriptionAddedToCreations(
        self,
    ):
        subscription = SubscriptionFactory.create(
            cancellation_ts=None,
            admin_confirmed=None,
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertEqual(
            result[subscription.member][subscription.product.type]["creations"],
            [subscription],
        )

    def test_buildChangesByMember_subscriptionCreationConfirmed_subscriptionNotAddedToCreations(
        self,
    ):
        subscription = SubscriptionFactory.create(
            cancellation_ts=None,
            admin_confirmed=timezone.now(),
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertNotIn(subscription.member, result.keys())

    def test_buildChangesByMember_subscriptionDeletionNotConfirmed_logEntryAddedToDeletions(
        self,
    ):
        log_entry = SubscriptionChangeLogEntry.objects.create(
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
            subscriptions="test",
            admin_confirmed=None,
            user=MemberFactory.create(),
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertEqual([log_entry], result[log_entry.user]["deleted"])

    def test_buildChangesByMember_subscriptionDeletionConfirmed_logEntryAddedToDeletions(
        self,
    ):
        log_entry = SubscriptionChangeLogEntry.objects.create(
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
            subscriptions="test",
            admin_confirmed=timezone.now(),
            user=MemberFactory.create(),
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertNotIn(log_entry.user, result.keys())

    def test_buildChangesByMember_memberHasUnconfirmedCoopSharePurchases_memberIsIncludedInResults(
        self,
    ):
        transaction = CoopShareTransactionFactory.create(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            admin_confirmed=None,
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        # Here we just need to make sure that the key exists. The actual value is set in build_data_to_confirm_for_member
        self.assertIn(transaction.member, result.keys())

    def test_buildChangesByMember_memberOnlyHasConfirmedCoopSharePurchases_memberIsNotIncludedInResults(
        self,
    ):
        transaction = CoopShareTransactionFactory.create(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            admin_confirmed=timezone.now(),
        )

        result = MemberDataToConfirmApiView.build_changes_by_member(cache={})

        self.assertNotIn(transaction.member, result.keys())
