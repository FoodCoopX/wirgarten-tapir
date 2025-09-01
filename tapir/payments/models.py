from django.db import models
from django.utils.translation import gettext_lazy as _

from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import format_date


class MemberPaymentRhythm(models.Model):
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
