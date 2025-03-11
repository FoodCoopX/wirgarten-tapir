from django.contrib.postgres.fields import ArrayField
from django.db import models

from tapir.core.models import TapirModel
from tapir.wirgarten.models import ExportedFile


class CsvExport(TapirModel):
    class AutomatedExportCycle(models.TextChoices):
        YEARLY = "yearly", "Jährlich"
        MONTHLY = "monthly", "Monatlich"
        WEEKLY = "weekly", "Wöchentlich"
        DAILY = "daily", "Täglich"
        NEVER = "never", "Nie"

    export_segment_id = models.CharField(max_length=512)
    name = models.CharField(max_length=512, unique=True)
    description = models.TextField(blank=True)
    separator = models.CharField(max_length=1)
    file_name = models.CharField(max_length=512)
    column_ids = ArrayField(
        base_field=models.CharField(max_length=512), default=list, blank=True
    )
    email_recipients = ArrayField(
        base_field=models.EmailField(), default=list, blank=True
    )
    automated_export_cycle = models.CharField(
        max_length=512, choices=AutomatedExportCycle.choices
    )
    automated_export_day = models.IntegerField()
    automated_export_hour = models.TimeField()


class AutomatedExportResult(TapirModel):
    export_definition = models.ForeignKey(CsvExport, on_delete=models.CASCADE)
    file = models.ForeignKey(ExportedFile, on_delete=models.CASCADE)
    datetime = models.DateTimeField()
