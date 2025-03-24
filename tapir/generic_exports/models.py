from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from tapir.core.models import TapirModel
from tapir.wirgarten.models import ExportedFile


class AutomatedExportCycle(models.TextChoices):
    YEARLY = "yearly", "Jährlich"
    MONTHLY = "monthly", "Monatlich"
    WEEKLY = "weekly", "Wöchentlich"
    DAILY = "daily", "Täglich"
    NEVER = "never", "Nie"


class CsvExport(TapirModel):
    export_segment_id = models.CharField(max_length=512)
    name = models.CharField(max_length=512, unique=True)
    description = models.TextField(blank=True)
    separator = models.CharField(max_length=1)
    file_name = models.CharField(max_length=512)
    column_ids = ArrayField(
        base_field=models.CharField(max_length=512, blank=True),
        default=list,
        blank=True,
    )
    custom_column_names = ArrayField(
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

    def __str__(self):
        return self.name

    def clean(self):
        if len(self.column_ids) != len(self.custom_column_names):
            raise ValidationError(
                f"There should be as many column ids as column names. IDs: {self.column_ids}, Names: {self.custom_column_names}"
            )


class AutomatedCsvExportResult(TapirModel):
    export_definition = models.ForeignKey(CsvExport, on_delete=models.CASCADE)
    file = models.ForeignKey(ExportedFile, on_delete=models.CASCADE)
    datetime = models.DateTimeField()


class PdfExport(TapirModel):
    export_segment_id = models.CharField(max_length=512)
    name = models.CharField(max_length=512, unique=True)
    description = models.TextField(blank=True)
    file_name = models.CharField(max_length=512)
    email_recipients = ArrayField(
        base_field=models.EmailField(), default=list, blank=True
    )
    automated_export_cycle = models.CharField(
        max_length=512, choices=AutomatedExportCycle.choices
    )
    automated_export_day = models.IntegerField()
    automated_export_hour = models.TimeField()
    template = models.TextField()
    generate_one_file_for_every_segment_entry = models.BooleanField()

    def __str__(self):
        return self.name


class AutomatedPdfExportResult(TapirModel):
    export_definition = models.ForeignKey(PdfExport, on_delete=models.CASCADE)
    file = models.ForeignKey(ExportedFile, on_delete=models.CASCADE)
    datetime = models.DateTimeField()
