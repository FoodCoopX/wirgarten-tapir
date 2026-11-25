import csv
import io
import uuid
from dataclasses import dataclass, field

from django.core.cache import cache as upload_cache
from django.core.files.uploadedfile import UploadedFile
from django.core.management.base import OutputWrapper
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.member_importer import MemberImporter
from tapir.utils.services.tabular_file_reader import TabularData, TabularFileReader
from tapir.wirgarten.models import Member


@dataclass
class MemberImportRowResult:
    line: int
    status: str
    error: str = ""


@dataclass
class MemberImportResult:
    rows: list[MemberImportRowResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    applied: bool = False

    @property
    def can_apply(self) -> bool:
        return (
            bool(self.rows)
            and not self.errors
            and not any(row.error for row in self.rows)
        )


class MemberImportService:
    COLUMNS = (
        "Nr",
        "Vorname",
        "Nachname",
        "Mailadresse",
        "consent_sepa",
        "Anrede",
        "Straße",
        "Hausnr.",
        "PLZ",
        "Ort",
        "Telefon",
        "Telefon 2",
        "Geburtstag/Gründungsdatum",
        "IBAN",
        "Kontoinhaber",
        "privacy_consent",
        "Pseudonym",
        "Abholort",
        "AO_gueltig_ab",
        "Zahlungsintervall",
        "Solidarpreis in EUR",
        "Solidarpreis Start_Date",
        "Solidarpreis End_Date",
        "Vereinsmitgliedschafttyp",
        "Vereinsmitgliedschaft Start_Date",
        "Vereinsmitgliedschaft End_Date",
    )
    EXAMPLE = {
        "Nr": "1",
        "Vorname": "Erika",
        "Nachname": "Musterfrau",
        "Mailadresse": "erika@example.org",
        "consent_sepa": "01.03.2024",
        "Anrede": "Liebe",
        "Straße": "Ackerweg",
        "Hausnr.": "1",
        "PLZ": "12345",
        "Ort": "Musterdorf",
        "Telefon": "+49 170 1234567",
        "Geburtstag/Gründungsdatum": "15.05.1980",
        "IBAN": "DE02120300000000202051",
        "Kontoinhaber": "Erika Musterfrau",
        "privacy_consent": "01.03.2024",
        "Zahlungsintervall": "Monatlich",
    }
    REQUIRED_COLUMNS = ("Nr", "Mailadresse")
    UPLOAD_TIMEOUT = 3600

    @staticmethod
    def upload_key(user_id: str, token: str) -> str:
        return f"member-import:{user_id}:{token}"

    @classmethod
    def preview(
        cls, file: UploadedFile, user_id: str
    ) -> tuple[str | None, MemberImportResult]:
        data = TabularFileReader.read(file)
        result = cls.run(data=data, dry_run=True)
        token = None
        if result.can_apply:
            token = uuid.uuid4().hex
            upload_cache.set(cls.upload_key(user_id, token), data, cls.UPLOAD_TIMEOUT)
        return token, result

    @classmethod
    def apply(cls, user_id: str, token: str) -> MemberImportResult:
        key = cls.upload_key(user_id, token)
        data = upload_cache.get(key)
        if data is None or not upload_cache.delete(key):
            raise TapirDataImportException(
                "Die geprüfte Datei ist abgelaufen. Bitte erneut hochladen."
            )
        return cls.run(data=data, dry_run=False)

    @classmethod
    def run(cls, data: TabularData, dry_run: bool) -> MemberImportResult:
        result = MemberImportResult()
        missing = [
            column for column in cls.REQUIRED_COLUMNS if column not in data.headers
        ]
        unknown = [column for column in data.headers if column not in cls.COLUMNS]
        if missing:
            result.errors.append("Fehlende Spalten: " + ", ".join(missing))
        if unknown:
            result.errors.append("Unbekannte Spalten: " + ", ".join(unknown))
        if result.errors:
            return result

        with transaction.atomic():
            for line, row in enumerate(data.rows, start=2):
                if not any(row.values()):
                    continue
                try:
                    with transaction.atomic():
                        member_no = int(row["Nr"])
                        if (
                            not Member.objects.filter(member_no=member_no).exists()
                            and TapirUser.objects.filter(
                                email__iexact=MemberImporter.build_mail(row, member_no),
                                member__isnull=True,
                            ).exists()
                        ):
                            raise TapirDataImportException(
                                "Für diese E-Mail-Adresse existiert bereits ein Benutzerkonto ohne Mitgliedschaft. "
                                "Diese Zuordnung wird im Mitgliederimport noch nicht unterstützt."
                            )
                        status = MemberImporter.import_member(
                            row=row,
                            update_existing=False,
                            dry_run=dry_run,
                            stdout=OutputWrapper(io.StringIO()),
                        )
                    label = {
                        MEMBER_IMPORT_STATUS_CREATED: "Neu",
                        MEMBER_IMPORT_STATUS_SKIPPED: "Bereits vorhanden – übersprungen",
                    }[status]
                    result.rows.append(MemberImportRowResult(line, label))
                except (TapirDataImportException, ValueError) as error:
                    result.rows.append(
                        MemberImportRowResult(line, "Fehler", str(error))
                    )

            if not result.rows:
                result.errors.append("Die Datei enthält keine Mitgliederzeilen.")
            if dry_run or not result.can_apply:
                transaction.set_rollback(True)
            else:
                result.applied = True
        return result

    @classmethod
    def build_template(cls) -> str:
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.writer(output, delimiter=";")
        writer.writerow(cls.COLUMNS)
        writer.writerow([cls.EXAMPLE.get(column, "") for column in cls.COLUMNS])
        return output.getvalue()
