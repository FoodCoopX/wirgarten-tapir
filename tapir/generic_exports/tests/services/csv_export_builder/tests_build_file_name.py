import datetime

from django.test import SimpleTestCase

from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder


class TestBuildFileName(SimpleTestCase):
    def test_buildFileName_extensionAlreadyInFileName_extensionNotDoubled(self):
        self.assertEqual(
            "test_name.2024.03.25 06.45.csv",
            CsvExportBuilder.build_file_name(
                "test_name.csv", datetime.datetime(2024, 3, 25, 6, 45)
            ),
        )

    def test_buildFileName_extensionNotInFileName_extensionAppended(self):
        self.assertEqual(
            "test_name.2024.03.25 06.45.csv",
            CsvExportBuilder.build_file_name(
                "test_name", datetime.datetime(2024, 3, 25, 6, 45)
            ),
        )
