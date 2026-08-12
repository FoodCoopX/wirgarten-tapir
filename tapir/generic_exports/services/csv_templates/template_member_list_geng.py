import datetime

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import AutomatedExportCycle, CsvExport, LocaleChoices
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider


class TemplateMemberListGeng:
    ID = "location_routes"
    NAME = "Mitgliederliste nach GenG."
    DESCRIPTION = "Erzeugt ein einziges CSV-Datei mit der Liste der Mitglieder nach Genossenschaftsgesetz."

    @classmethod
    def create_exports(cls):
        export_name = cls.NAME
        if CsvExport.objects.filter(name=export_name).exists():
            raise TemplateAlreadyExistsException(
                f'Ein CSV-Export mit dem Namen "{export_name}"  existiert bereits. Falls dieser neu erzeugt werden soll, bitte zuerst den alten Export-Eintrag aus der Liste löschen.'
            )

        column_ids = [
            MemberColumnProvider.COLUMN_ID_MEMBER_NUMBER,
            MemberColumnProvider.COLUMN_ID_LAST_NAME,
            MemberColumnProvider.COLUMN_ID_FIRST_NAME,
            MemberColumnProvider.COLUMN_ID_FULL_ADDRESS,
            MemberColumnProvider.COLUMN_ID_ADMISSION_DATE,
            MemberColumnProvider.COLUMN_ID_SHARE_QUANTITY,
            MemberColumnProvider.COLUMN_ID_SHARE_HISTORY,
            MemberColumnProvider.COLUMN_ID_TERMINATION_DATE,
        ]

        CsvExport.objects.create(
            name=export_name,
            export_segment_id=MemberSegmentProvider.SEGMENT_ID_ALL_MEMBERS,
            file_name="GenG. Mitgliederliste.csv",
            automated_export_cycle=AutomatedExportCycle.NEVER,
            automated_export_day=365,
            automated_export_hour=datetime.time(hour=23),
            separator=",",
            locale=LocaleChoices.DE,
            column_ids=column_ids,
            custom_column_names=[
                cls.get_default_column_name(column_id) for column_id in column_ids
            ],
        )

    @classmethod
    def get_default_column_name(cls, column_id: str):
        for column in MemberColumnProvider.get_member_columns():
            if column.id == column_id:
                return column.display_name

        raise TapirImproperlyConfigured(f"No column with id {column_id} found")
