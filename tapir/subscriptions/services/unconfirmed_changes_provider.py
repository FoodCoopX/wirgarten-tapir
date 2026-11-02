from django.db.models import QuerySet

from tapir.wirgarten.models import (
    Subscription,
    SubscriptionChangeLogEntry,
    CoopShareTransaction,
)


class UnconfirmedChangesProvider:
    @classmethod
    def get_unconfirmed_cancellations(cls) -> QuerySet[Subscription]:
        return Subscription.objects.filter(
            cancellation_ts__isnull=False,
            cancellation_admin_confirmed__isnull=True,
        )

    @classmethod
    def get_unconfirmed_creations(cls) -> QuerySet[Subscription]:
        return Subscription.objects.filter(
            admin_confirmed__isnull=True,
            cancellation_ts__isnull=True,
        )

    @classmethod
    def get_unconfirmed_deletions(cls) -> QuerySet[SubscriptionChangeLogEntry]:
        return SubscriptionChangeLogEntry.objects.filter(
            admin_confirmed__isnull=True,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
        )

    @classmethod
    def get_unconfirmed_share_purchases(cls) -> QuerySet[CoopShareTransaction]:
        return CoopShareTransaction.objects.filter(
            admin_confirmed__isnull=True,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        )
