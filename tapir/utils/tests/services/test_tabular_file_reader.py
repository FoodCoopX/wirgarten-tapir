import datetime
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from openpyxl import Workbook

from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.tabular_file_reader import TabularFileReader


class TestTabularFileReader(SimpleTestCase):
    def test_read_csvWithBomAndBlankRow_preservesLineNumbers(self):
        file = SimpleUploadedFile(
            "members.csv", "\ufeffNr;Mailadresse\n\n101;mika@example.test\n".encode()
        )

        result = TabularFileReader.read(file)

        self.assertEqual(["Nr", "Mailadresse"], result.headers)
        self.assertEqual("", result.rows[0]["Nr"])
        self.assertEqual("101", result.rows[1]["Nr"])

    def test_read_excel_convertsDatesAndNumbers(self):
        workbook = Workbook()
        workbook.active.append(["Nr", "consent_sepa"])
        workbook.active.append([101, datetime.datetime(2024, 3, 1)])
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        result = TabularFileReader.read(
            SimpleUploadedFile("members.xlsx", output.getvalue())
        )

        self.assertEqual({"Nr": "101", "consent_sepa": "2024-03-01"}, result.rows[0])

    def test_read_invalidFiles_returnsImportError(self):
        for name, content in (
            ("members.csv", b'Nr;Mailadresse\n101;"unfinished'),
            ("members.csv", b"Nr;Nr\n101;102"),
            ("members.csv", b"Nr;Mailadresse\n101;mika@example.test;extra"),
            ("members.csv", b""),
            ("members.xlsx", b"not a workbook"),
            ("members.txt", b"Nr;Mailadresse"),
        ):
            with self.subTest(name=name, content=content):
                with self.assertRaises(TapirDataImportException):
                    TabularFileReader.read(SimpleUploadedFile(name, content))
