import datetime
from unittest.mock import patch, Mock, call

from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestCreateExportedFiles(TapirUnitTest):
    @patch.object(PdfExportBuilder, "create_single_file", autospec=True)
    @patch.object(PdfExportBuilder, "build_contexts", autospec=True)
    def test_createExportedFiles_generateSingleExport_createsOneFile(
        self, mock_build_contexts: Mock, mock_create_single_file: Mock
    ):
        mock_export = Mock()
        mock_export.generate_one_file_for_every_segment_entry = False
        reference_datetime = datetime.datetime(year=2015, month=1, day=2)
        mock_contexts = {"some_key": "some_value"}
        mock_build_contexts.return_value = mock_contexts
        mock_created_file = Mock()
        mock_create_single_file.return_value = mock_created_file
        mock_timezone(test=self, now=datetime.datetime(year=2015, month=4, day=7))

        result = PdfExportBuilder.create_exported_files(mock_export, reference_datetime)

        self.assertEqual([mock_created_file], result)
        mock_build_contexts.assert_called_once_with(
            mock_export, reference_datetime, cache={}
        )
        mock_create_single_file.assert_called_once_with(
            mock_export,
            reference_datetime,
            {
                "entries": mock_contexts,
                "today": datetime.date(year=2015, month=4, day=7),
                "reference_date": datetime.date(year=2015, month=1, day=2),
            },
        )

    @patch.object(PdfExportBuilder, "create_single_file", autospec=True)
    @patch.object(PdfExportBuilder, "build_contexts", autospec=True)
    def test_createExportedFiles_generateMultipleExport_createsMultipleFiles(
        self, mock_build_contexts: Mock, mock_create_single_file: Mock
    ):
        mock_export = Mock()
        mock_export.generate_one_file_for_every_segment_entry = True
        reference_datetime = datetime.datetime(year=2016, month=9, day=3)
        mock_contexts = [{"aa": "bb"}, {"cc": "dd"}, {"ee": "ff"}]
        mock_build_contexts.return_value = mock_contexts
        mock_created_files = [Mock(), Mock(), Mock()]
        mock_create_single_file.side_effect = mock_created_files
        mock_timezone(test=self, now=datetime.datetime(year=2016, month=11, day=27))

        result = PdfExportBuilder.create_exported_files(mock_export, reference_datetime)

        self.assertEqual(mock_created_files, result)
        mock_build_contexts.assert_called_once_with(
            mock_export, reference_datetime, cache={}
        )
        self.assertEqual(3, mock_create_single_file.call_count)
        mock_create_single_file.assert_has_calls(
            [
                call(
                    mock_export,
                    reference_datetime,
                    context
                    | {
                        "today": datetime.date(year=2016, month=11, day=27),
                        "reference_date": datetime.date(year=2016, month=9, day=3),
                    },
                )
                for context in mock_contexts
            ]
        )
