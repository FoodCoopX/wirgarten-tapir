import datetime
import io

from django.test import SimpleTestCase
from openpyxl import Workbook

from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.tabular_file_reader import TabularFileReader


def build_excel(rows: list[list]) -> io.BytesIO:
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


class TestTabularFileReader(SimpleTestCase):
    def test_read_excel_typedCells_convertedToTheStringsTheImportersExpect(self):
        file = build_excel(
            [
                ["Nr", "﻿Vorname\xa0", "consent_sepa", "Betrag", "Probezeit", "Leer"],
                [7, "Erika", datetime.datetime(2024, 3, 1), 12.5, True, None],
                [8.0, "Max", datetime.datetime(2024, 3, 1, 14, 30), 10.0, False, ""],
            ]
        )

        data = TabularFileReader.read(file, "Mitglieder.xlsx")

        self.assertEqual(
            ["Nr", "Vorname", "consent_sepa", "Betrag", "Probezeit", "Leer"],
            data.headers,
        )
        self.assertEqual(
            [
                {
                    "Nr": "7",
                    "Vorname": "Erika",
                    "consent_sepa": "2024-03-01",
                    "Betrag": "12.5",
                    "Probezeit": "true",
                    "Leer": "",
                },
                {
                    "Nr": "8",
                    "Vorname": "Max",
                    "consent_sepa": "2024-03-01T14:30:00",
                    "Betrag": "10",
                    "Probezeit": "false",
                    "Leer": "",
                },
            ],
            data.rows,
        )

    def test_read_csvWithSemicolonAndBom_returnsRows(self):
        content = "﻿Nr;Vorname\n1;Erika\n".encode("utf-8")

        data = TabularFileReader.read(io.BytesIO(content), "mitglieder.csv")

        self.assertEqual(["Nr", "Vorname"], data.headers)
        self.assertEqual([{"Nr": "1", "Vorname": "Erika"}], data.rows)

    def test_read_csvWithCommaInWindowsEncoding_returnsRows(self):
        content = "Nr,Straße\n1,Gärtnerweg\n".encode("cp1252")

        data = TabularFileReader.read(io.BytesIO(content), "mitglieder.CSV")

        self.assertEqual([{"Nr": "1", "Straße": "Gärtnerweg"}], data.rows)

    def test_read_unknownExtension_raisesException(self):
        with self.assertRaises(TapirDataImportException):
            TabularFileReader.read(io.BytesIO(b""), "mitglieder.ods")
