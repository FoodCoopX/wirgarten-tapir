from django.db import models

from tapir.accounts.models import TapirUser
from tapir.core.models import TapirModel
from tapir.log.models import LogEntry
from tapir.wirgarten.models import Member


class SolidarityContribution(TapirModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    start_date = models.DateField()
    end_date = models.DateField()
    trial_disabled = models.BooleanField(default=False)
    trial_end_date_override = models.DateField(null=True)
    cancellation_ts = models.DateField(null=True)

    def __str__(self):
        return f"{self.member} - {self.amount} - {self.start_date} - {self.end_date}"


class SolidarityContributionChangedLogEntry(LogEntry):
    template_name = (
        "solidarity_contribution/log/solidarity_contribution_changed_log_entry.html"
    )
    old_contribution_amount = models.DecimalField(decimal_places=2, max_digits=12)
    old_contribution_end_date = models.DateField(null=True)
    new_contribution_amount = models.DecimalField(decimal_places=2, max_digits=12)
    new_contribution_start_date = models.DateField(null=True)

    old_contribution = models.ForeignKey(
        SolidarityContribution,
        on_delete=models.SET_NULL,
        null=True,
        related_name="changed_logs_old_contribution",
    )
    new_contribution = models.ForeignKey(
        SolidarityContribution,
        on_delete=models.SET_NULL,
        null=True,
        related_name="changed_logs_new_contribution",
    )

    def populate_solidarity_contribution(
        self,
        actor: TapirUser | None,
        user: TapirUser | None,
        old_contribution: SolidarityContribution | None,
        new_contribution: SolidarityContribution | None,
    ):
        super().populate(actor, user)

        if old_contribution is None:
            self.old_contribution_amount = 0
            self.old_contribution_end_date = None
        else:
            # We must check if that contribution object still exists in the DB, it may have been deleted in between
            self.old_contribution = SolidarityContribution.objects.filter(
                id=old_contribution.id
            ).first()

            self.old_contribution_amount = old_contribution.amount
            self.old_contribution_end_date = old_contribution.end_date

        self.new_contribution = new_contribution
        if new_contribution is None:
            self.new_contribution_amount = 0
            self.new_contribution_start_date = None
        else:
            self.new_contribution_amount = new_contribution.amount
            self.new_contribution_start_date = new_contribution.start_date

        return self

    def get_context_data(self):
        context_data = super().get_context_data()
        context_data["old_contribution_amount"] = self.old_contribution_amount
        context_data["new_contribution_amount"] = self.new_contribution_amount
        context_data["old_contribution_end_date"] = self.old_contribution_end_date
        context_data["new_contribution_start_date"] = self.new_contribution_start_date
        return context_data
