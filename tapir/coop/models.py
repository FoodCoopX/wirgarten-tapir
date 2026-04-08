from django.db import models

from tapir.log.models import LogEntry
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.utils import format_date


class CoopSharesRevokedLogEntry(LogEntry):
    template_name = "coop/log/coop_shares_revoked_log_entry.html"

    coop_share_transactions = models.CharField(null=False, blank=False, max_length=1024)

    def populate_transactions(
        self, coop_share_transactions: list[CoopShareTransaction], actor, user
    ):
        self.populate(actor=actor, user=user)
        self.coop_share_transactions = self.format_coop_share_transactions(
            coop_share_transactions
        )
        return self

    @classmethod
    def format_coop_share_transactions(cls, coop_share_transactions):
        return ", ".join(
            [
                f"{transaction.quantity} Genossenschaftsanteilen die am {format_date(transaction.valid_at)} gültig geworden wären"
                for transaction in coop_share_transactions
            ]
        )


class CoopSharesPurchasedLogEntry(LogEntry):
    template_name = "coop/log/coop_shares_purchased_log_entry.html"

    coop_share_transaction = models.CharField(null=False, blank=False, max_length=1024)

    @classmethod
    def populate_transaction(
        cls, coop_share_transaction: CoopShareTransaction, actor, user
    ):
        log_entry = cls()
        log_entry.populate(actor=actor, user=user)
        log_entry.coop_share_transaction = f"{coop_share_transaction.quantity} Genossenschaftsanteilen die am {format_date(coop_share_transaction.valid_at)} gültig werden"
        return log_entry


class CoopSharesCancelledLogEntry(LogEntry):
    template_name = "coop/log/coop_shares_cancelled_log_entry.html"

    nb_shares = models.IntegerField()
    cancellation_valid_at = models.DateField()

    @classmethod
    def populate_transaction(
        cls, coop_share_transaction: CoopShareTransaction, actor, user
    ):
        log_entry = cls()
        log_entry.populate(actor=actor, user=user)
        log_entry.nb_shares = coop_share_transaction.quantity
        log_entry.cancellation_valid_at = coop_share_transaction.valid_at
        return log_entry
