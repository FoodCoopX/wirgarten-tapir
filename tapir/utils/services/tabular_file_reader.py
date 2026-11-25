import csv
import datetime
import io
from dataclasses import dataclass
from decimal import Decimal
from zipfile import BadZipFile

from django.core.files.uploadedfile import UploadedFile
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from tapir.utils.exceptions import TapirDataImportException


@dataclass
class TabularData:
    headers: list[str]
    rows: list[dict[str, str]]


class TabularFileReader:
    @classmethod
    def read(cls, file: UploadedFile) -> TabularData:
        if file.name.lower().endswith(".csv"):
            content = file.read()
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    text = content.decode("cp1252")
                except UnicodeDecodeError as error:
                    raise TapirDataImportException(
                        "Die CSV-Datei kann nicht gelesen werden."
                    ) from error
            first_line = text.split("\n", 1)[0]
            separator = ";" if first_line.count(";") >= first_line.count(",") else ","
            try:
                return cls.read_rows(
                    csv.reader(
                        io.StringIO(text, newline=""), delimiter=separator, strict=True
                    )
                )
            except csv.Error as error:
                raise TapirDataImportException(
                    "Die CSV-Datei kann nicht gelesen werden."
                ) from error

        if not file.name.lower().endswith(".xlsx"):
            raise TapirDataImportException(
                "Bitte eine CSV- oder Excel-Datei (.xlsx) hochladen."
            )

        try:
            workbook = load_workbook(file, read_only=True, data_only=True)
        except (BadZipFile, InvalidFileException, OSError, ValueError) as error:
            raise TapirDataImportException(
                "Die Excel-Datei kann nicht gelesen werden."
            ) from error

        try:
            return cls.read_rows(workbook.worksheets[0].iter_rows(values_only=True))
        finally:
            workbook.close()

    @classmethod
    def read_rows(cls, rows) -> TabularData:
        rows = iter(rows)
        headers = [cls.cell_to_string(value).strip() for value in next(rows, [])]
        if not any(headers):
            raise TapirDataImportException(
                "Die Tabelle hat keine Spaltenüberschriften."
            )

        named_headers = [header for header in headers if header]
        if len(named_headers) != len(set(named_headers)):
            raise TapirDataImportException(
                "Eine Spaltenüberschrift kommt mehrfach vor."
            )

        result = []
        for line, values in enumerate(rows, start=2):
            values = [cls.cell_to_string(value) for value in values]
            if not any(values):
                result.append({header: "" for header in named_headers})
                continue

            if len(values) > len(headers) or any(
                not header and value for header, value in zip(headers, values)
            ):
                raise TapirDataImportException(
                    f"Zeile {line}: Werte ohne Spaltenüberschrift."
                )

            values += [""] * (len(headers) - len(values))
            result.append(
                {header: value for header, value in zip(headers, values) if header}
            )
        return TabularData(headers=named_headers, rows=result)

    @staticmethod
    def cell_to_string(value) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime.datetime):
            return (
                value.date().isoformat()
                if value.time() == datetime.time()
                else value.isoformat()
            )
        if isinstance(value, datetime.date):
            return value.isoformat()
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            return (
                str(int(value))
                if value.is_integer()
                else format(Decimal(str(value)).normalize(), "f")
            )
        return str(value).strip()
