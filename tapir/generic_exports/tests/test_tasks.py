from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.generic_exports import tasks
from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)


class TestTasks(SimpleTestCase):
    @patch.object(AutomatedExportsManager, "do_automated_pdf_exports")
    @patch.object(AutomatedExportsManager, "do_automated_csv_exports")
    def test_doAutomatedExports_default_callsService(
        self, mock_do_automated_csv_exports: Mock, mock_do_automated_pdf_exports: Mock
    ):
        tasks.do_automated_exports()
        mock_do_automated_csv_exports.assert_called_once_with()
        mock_do_automated_pdf_exports.assert_called_once_with()
