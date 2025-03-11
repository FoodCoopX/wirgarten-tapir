import datetime

from django.db import transaction

from tapir.generic_exports.models import CsvExport, AutomatedExportResult
from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.wirgarten.utils import get_now


class AutomatedExportsManager:
    @classmethod
    def do_automated_exports(cls):
        for export in CsvExport.objects.exclude(
            automated_export_cycle=CsvExport.AutomatedExportCycle.NEVER
        ):
            datetime_of_last_export = cls.get_datetime_of_latest_export(export)
            if AutomatedExportResult.objects.filter(
                export_definition=export,
                datetime__year=datetime_of_last_export.year,
                datetime__month=datetime_of_last_export.month,
                datetime__day=datetime_of_last_export.day,
                datetime__hour=datetime_of_last_export.hour,
                datetime__minute=datetime_of_last_export.minute,
            ).exists():
                continue
            cls.do_export(export, datetime_of_last_export)

    @classmethod
    @transaction.atomic
    def do_export(cls, export, reference_datetime):
        file = CsvExportBuilder.create_exported_file(export, reference_datetime)
        AutomatedExportResult.objects.create(
            export_definition=export, datetime=reference_datetime, file=file
        )

    @classmethod
    def get_datetime_of_latest_export(cls, export: CsvExport):
        if export.automated_export_cycle == CsvExport.AutomatedExportCycle.YEARLY:
            return cls.get_datetime_of_latest_yearly_export(export)
        if export.automated_export_cycle == CsvExport.AutomatedExportCycle.MONTHLY:
            return cls.get_datetime_of_latest_monthly_export(export)
        if export.automated_export_cycle == CsvExport.AutomatedExportCycle.WEEKLY:
            return cls.get_datetime_of_latest_weekly_export(export)
        if export.automated_export_cycle == CsvExport.AutomatedExportCycle.DAILY:
            return cls.get_datetime_of_latest_daily_export(export)

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
        return start_of_previous_month + datetime.timedelta(
            days=export.automated_export_day - 1
        )

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
        return start_of_previous_week + datetime.timedelta(
            days=export.automated_export_day - 1
        )

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
