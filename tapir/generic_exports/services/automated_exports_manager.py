import datetime

from django.db import transaction

from tapir.generic_exports.models import (
    CsvExport,
    AutomatedCsvExportResult,
    AutomatedExportCycle,
    PdfExport,
    AutomatedPdfExportResult,
)
from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.services.export_mail_sender import ExportMailSender
from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.wirgarten.utils import get_now


class AutomatedExportsManager:
    @classmethod
    def do_automated_csv_exports(cls):
        for export in CsvExport.objects.exclude(
            automated_export_cycle=AutomatedExportCycle.NEVER
        ):
            datetime_of_last_export = cls.get_datetime_of_latest_export(export)
            # There is at most one export a day, so it is enough to check of the date
            # Checking for the time is tricky because if timezones.
            if AutomatedCsvExportResult.objects.filter(
                export_definition=export, datetime__date=datetime_of_last_export.date()
            ).exists():
                continue
            cls.do_single_csv_export(export, datetime_of_last_export)

    @classmethod
    @transaction.atomic
    def do_single_csv_export(cls, export, reference_datetime):
        file = CsvExportBuilder.create_exported_file(export, reference_datetime)
        result = AutomatedCsvExportResult.objects.create(
            export_definition=export, datetime=reference_datetime, file=file
        )
        ExportMailSender.send_mails_for_export([result])

    @classmethod
    def do_automated_pdf_exports(cls):
        for export in PdfExport.objects.exclude(
            automated_export_cycle=AutomatedExportCycle.NEVER
        ):
            datetime_of_last_export = cls.get_datetime_of_latest_export(export)
            if AutomatedPdfExportResult.objects.filter(
                export_definition=export, datetime__date=datetime_of_last_export.date()
            ).exists():
                continue
            cls.do_single_pdf_export(export, datetime_of_last_export)

    @classmethod
    @transaction.atomic
    def do_single_pdf_export(cls, export, reference_datetime):
        files = PdfExportBuilder.create_exported_files(export, reference_datetime)
        results = [
            AutomatedCsvExportResult.objects.create(
                export_definition=export, datetime=reference_datetime, file=file
            )
            for file in files
        ]
        ExportMailSender.send_mails_for_export(results)

    @classmethod
    def get_datetime_of_latest_export(cls, export: CsvExport | PdfExport):
        if export.automated_export_cycle == AutomatedExportCycle.YEARLY:
            return cls.get_datetime_of_latest_yearly_export(export)
        if export.automated_export_cycle == AutomatedExportCycle.MONTHLY:
            return cls.get_datetime_of_latest_monthly_export(export)
        if export.automated_export_cycle == AutomatedExportCycle.WEEKLY:
            return cls.get_datetime_of_latest_weekly_export(export)
        if export.automated_export_cycle == AutomatedExportCycle.DAILY:
            return cls.get_datetime_of_latest_daily_export(export)
        return None

    @classmethod
    def get_datetime_of_latest_yearly_export(cls, export: CsvExport):
        now = get_now()
        start_of_year = now.replace(month=1, day=1)
        result = start_of_year + datetime.timedelta(
            days=export.automated_export_day - 1
        )
        result = cls.set_time(result, export.automated_export_hour)
        if result < now:
            return result

        return result.replace(year=result.year - 1)

    @classmethod
    def get_datetime_of_latest_monthly_export(cls, export: CsvExport):
        now = get_now()
        start_of_month = now.replace(day=1)
        result = start_of_month + datetime.timedelta(
            days=export.automated_export_day - 1
        )
        result = cls.set_time(result, export.automated_export_hour)
        if result < now:
            return result

        start_of_previous_month = (
            now.replace(day=1) - datetime.timedelta(days=1)
        ).replace(day=1)
        result = start_of_previous_month + datetime.timedelta(
            days=export.automated_export_day - 1
        )
        result = cls.set_time(result, export.automated_export_hour)
        return result

    @classmethod
    def get_datetime_of_latest_weekly_export(cls, export: CsvExport):
        now = get_now()
        start_of_week = now - datetime.timedelta(days=now.weekday())
        result = start_of_week + datetime.timedelta(
            days=export.automated_export_day - 1
        )
        result = cls.set_time(result, export.automated_export_hour)
        if result < now:
            return result

        start_of_previous_week = start_of_week - datetime.timedelta(days=7)
        result = start_of_previous_week + datetime.timedelta(
            days=export.automated_export_day - 1
        )
        result = cls.set_time(result, export.automated_export_hour)
        return result

    @classmethod
    def get_datetime_of_latest_daily_export(cls, export: CsvExport):
        now = get_now()
        result = cls.set_time(now, export.automated_export_hour)
        if result < now:
            return result

        return result - datetime.timedelta(days=1)

    @classmethod
    def set_time(cls, dt: datetime.datetime, time: datetime.time):
        return dt.replace(hour=time.hour, minute=time.minute)
