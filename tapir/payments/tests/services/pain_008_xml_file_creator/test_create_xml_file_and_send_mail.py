from unittest.mock import patch, MagicMock

from tapir.payments.services.pain_008_xml_file_creator import Pain008XmlFileCreator
from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlGlobalException,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.models import ExportedFile
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCreateXmlFileAndSendMail(TapirUnitTest):
    @patch(
        "tapir.payments.services.pain_008_xml_file_creator.export_file", autospec=True
    )
    @patch.object(
        Pain008XmlFileCreator,
        "build_xml_string_with_valid_payments_and_errors_for_invalid_payments",
        autospec=True,
    )
    def test_createXmlFileAndSendMail_xmlStringBuiltWithoutErrors_returnsExportedFile(
        self,
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments: MagicMock,
        mock_export_file: MagicMock,
    ):
        xml_bytes = MagicMock()
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.return_value = (
            xml_bytes,
            [],
        )

        xml_file = MagicMock()
        mock_export_file.return_value = xml_file

        payments = MagicMock()
        file_name = MagicMock()
        reference_date = MagicMock()
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.PAYMENT_SEND_XML_FILE_PER_MAIL, value=True
        )

        result = Pain008XmlFileCreator.create_xml_file_and_send_mail(
            payments=payments,
            file_name=file_name,
            reference_date=reference_date,
            send_mail=True,
            cache=cache,
        )

        self.assertEqual((xml_file, []), result)

        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.assert_called_once_with(
            payments=payments, collection_date=reference_date, cache=cache
        )
        mock_export_file.assert_called_once_with(
            filename=file_name,
            filetype=ExportedFile.FileType.XML,
            content=xml_bytes,
            send_email=True,
            cache=cache,
            errors=[],
        )

    @patch(
        "tapir.payments.services.pain_008_xml_file_creator.export_file", autospec=True
    )
    @patch.object(
        Pain008XmlFileCreator,
        "build_xml_string_with_valid_payments_and_errors_for_invalid_payments",
        autospec=True,
    )
    def test_createXmlFileAndSendMail_mailSendingDisabledByConfig_dontSendExportedFile(
        self,
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments: MagicMock,
        mock_export_file: MagicMock,
    ):
        xml_bytes = MagicMock()
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.return_value = (
            xml_bytes,
            [],
        )

        xml_file = MagicMock()
        mock_export_file.return_value = xml_file

        payments = MagicMock()
        file_name = MagicMock()
        reference_date = MagicMock()
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.PAYMENT_SEND_XML_FILE_PER_MAIL, value=False
        )

        result = Pain008XmlFileCreator.create_xml_file_and_send_mail(
            payments=payments,
            file_name=file_name,
            reference_date=reference_date,
            send_mail=True,
            cache=cache,
        )

        self.assertEqual((xml_file, []), result)

        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.assert_called_once_with(
            payments=payments, collection_date=reference_date, cache=cache
        )
        mock_export_file.assert_called_once_with(
            filename=file_name,
            filetype=ExportedFile.FileType.XML,
            content=xml_bytes,
            send_email=False,
            cache=cache,
            errors=[],
        )

    @patch(
        "tapir.payments.services.pain_008_xml_file_creator.export_file", autospec=True
    )
    @patch.object(
        Pain008XmlFileCreator,
        "build_xml_string_with_valid_payments_and_errors_for_invalid_payments",
        autospec=True,
    )
    def test_createXmlFileAndSendMail_mailSendingDisabledByParameter_dontSendExportedFile(
        self,
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments: MagicMock,
        mock_export_file: MagicMock,
    ):
        xml_bytes = MagicMock()
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.return_value = (
            xml_bytes,
            [],
        )

        xml_file = MagicMock()
        mock_export_file.return_value = xml_file

        payments = MagicMock()
        file_name = MagicMock()
        reference_date = MagicMock()
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.PAYMENT_SEND_XML_FILE_PER_MAIL, value=True
        )

        result = Pain008XmlFileCreator.create_xml_file_and_send_mail(
            payments=payments,
            file_name=file_name,
            reference_date=reference_date,
            send_mail=False,
            cache=cache,
        )

        self.assertEqual((xml_file, []), result)

        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.assert_called_once_with(
            payments=payments, collection_date=reference_date, cache=cache
        )
        mock_export_file.assert_called_once_with(
            filename=file_name,
            filetype=ExportedFile.FileType.XML,
            content=xml_bytes,
            send_email=False,
            cache=cache,
            errors=[],
        )

    @patch(
        "tapir.payments.services.pain_008_xml_file_creator.export_file", autospec=True
    )
    @patch.object(
        Pain008XmlFileCreator, "send_error_mail_or_raise_exception", autospec=True
    )
    @patch.object(
        Pain008XmlFileCreator,
        "build_xml_string_with_valid_payments_and_errors_for_invalid_payments",
        autospec=True,
    )
    def test_createXmlFileAndSendMail_globalExceptionRaised_sendErrorMailAndDontExportFile(
        self,
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments: MagicMock,
        mock_send_error_mail_or_raise_exception: MagicMock,
        mock_export_file: MagicMock,
    ):
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.side_effect = Pain008XmlGlobalException(
            message="test_message"
        )

        payments = MagicMock()
        file_name = MagicMock()
        reference_date = MagicMock()
        send_mail = MagicMock()
        cache = MagicMock()

        result = Pain008XmlFileCreator.create_xml_file_and_send_mail(
            payments=payments,
            file_name=file_name,
            reference_date=reference_date,
            send_mail=send_mail,
            cache=cache,
        )

        self.assertEqual((None, []), result)

        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.assert_called_once_with(
            payments=payments, collection_date=reference_date, cache=cache
        )
        mock_send_error_mail_or_raise_exception.assert_called_once_with(
            reason="test_message", file_name=file_name, cache=cache, send_mail=send_mail
        )
        mock_export_file.assert_not_called()

    @patch(
        "tapir.payments.services.pain_008_xml_file_creator.export_file", autospec=True
    )
    @patch.object(
        Pain008XmlFileCreator,
        "build_xml_string_with_valid_payments_and_errors_for_invalid_payments",
        autospec=True,
    )
    def test_createXmlFileAndSendMail_somePaymentFails_buildOnlyValidPaymentsAndSendFileWithDetailsOfAllErrors(
        self,
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments: MagicMock,
        mock_export_file: MagicMock,
    ):
        xml_bytes = MagicMock()
        errors_failed_payments = ["error_1", "error_2"]
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.return_value = (
            xml_bytes,
            errors_failed_payments,
        )

        xml_file = MagicMock()
        mock_export_file.return_value = xml_file

        payments = MagicMock()
        file_name = MagicMock()
        reference_date = MagicMock()
        cache = MagicMock()

        result = Pain008XmlFileCreator.create_xml_file_and_send_mail(
            payments=payments,
            file_name=file_name,
            reference_date=reference_date,
            send_mail=False,
            cache=cache,
        )

        self.assertEqual((xml_file, errors_failed_payments), result)

        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.assert_called_once_with(
            payments=payments, collection_date=reference_date, cache=cache
        )
        mock_export_file.assert_called_once_with(
            filename=file_name,
            filetype=ExportedFile.FileType.XML,
            content=xml_bytes,
            send_email=False,
            cache=cache,
            errors=errors_failed_payments,
        )

    @patch(
        "tapir.payments.services.pain_008_xml_file_creator.export_file", autospec=True
    )
    @patch.object(
        Pain008XmlFileCreator, "send_error_mail_or_raise_exception", autospec=True
    )
    @patch.object(
        Pain008XmlFileCreator,
        "build_xml_string_with_valid_payments_and_errors_for_invalid_payments",
        autospec=True,
    )
    def test_createXmlFileAndSendMail_allPaymentsFail_sendErrorMailAndDontExportFile(
        self,
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments: MagicMock,
        mock_send_error_mail_or_raise_exception: MagicMock,
        mock_export_file: MagicMock,
    ):
        errors_failed_payments = ["error_1", "error_2"]
        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.return_value = (
            None,
            errors_failed_payments,
        )

        payments = MagicMock()
        file_name = MagicMock()
        reference_date = MagicMock()
        send_mail = MagicMock()
        cache = MagicMock()

        result = Pain008XmlFileCreator.create_xml_file_and_send_mail(
            payments=payments,
            file_name=file_name,
            reference_date=reference_date,
            send_mail=send_mail,
            cache=cache,
        )

        self.assertEqual((None, []), result)

        mock_build_xml_string_with_valid_payments_and_errors_for_invalid_payments.assert_called_once_with(
            payments=payments, collection_date=reference_date, cache=cache
        )
        mock_send_error_mail_or_raise_exception.assert_called_once_with(
            reason="<ul><li>error_1</li><li>error_2</li></ul>",
            file_name=file_name,
            cache=cache,
            send_mail=send_mail,
        )
        mock_export_file.assert_not_called()
