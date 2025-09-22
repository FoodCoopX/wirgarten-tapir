import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _

from tapir.core.models import TapirModel
from tapir.log.models import LogEntry
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import format_date


class MemberPaymentRhythm(TapirModel):
    class Rhythm(models.TextChoices):
        MONTHLY = "monthly", _("Monatlich")
        QUARTERLY = "quarterly", _("Vierteljährlich")
        SEMIANNUALLY = "semiannually", _("Halbjährlich")
        YEARLY = "yearly", _("Jährlich")

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    rhythm = models.CharField(choices=Rhythm, max_length=20)
    valid_from = models.DateField()

    def __str__(self):
        return f"{self.member} - {self.rhythm} - {format_date(self.valid_from)}"


class MemberPaymentRhythmChangeLogEntry(LogEntry):
    template_name = "payments/log/member_payment_change_log_entry.html"

    old_rhythm = models.CharField()
    new_rhythm = models.CharField()
    valid_from = models.DateField()

    def populate_rhythm(
        self,
        old_rhythm: str,
        new_rhythm: str,
        valid_from: datetime.date,
        actor=None,
        user=None,
    ):
        super().populate(actor=actor, user=user)
        self.old_rhythm = old_rhythm
        self.new_rhythm = new_rhythm
        self.valid_from = valid_from

        return self

    def get_context_data(self):
        from tapir.payments.services.member_payment_rhythm_service import (
            MemberPaymentRhythmService,
        )

        context_data = super().get_context_data()
        context_data["old_rhythm"] = MemberPaymentRhythmService.get_rhythm_display_name(
            self.old_rhythm
        )
        context_data["new_rhythm"] = MemberPaymentRhythmService.get_rhythm_display_name(
            self.new_rhythm
        )
        context_data["valid_from"] = format_date(self.valid_from)
        return context_data
