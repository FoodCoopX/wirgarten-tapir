from django.db import models

from tapir.log.models import LogEntry
from tapir.wirgarten.utils import format_date


class CoopSharesRevokedLogEntry(LogEntry):
    template_name = "coop/log/coop_shares_revoked_log_entry.html"

    coop_share_transactions = models.CharField(null=False, blank=False, max_length=1024)

    def populate_transactions(self, coop_share_transactions, actor, user):
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
