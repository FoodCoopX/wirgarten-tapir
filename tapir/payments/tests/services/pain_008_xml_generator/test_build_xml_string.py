import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError
from lxml import etree

from tapir.payments.services.pain_008_xml_generator import Pain008XmlGenerator
from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


class TestBuildXmlString(TapirUnitTest):
    def setUp(self) -> None:
        self.cache = {}
        mock_parameter_value(
            cache=self.cache, key=ParameterKeys.SITE_NAME, value="Test-site-name"
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN,
            value="DE60500105172436256838",
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_ORGANISATION_BIC,
            value="",
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER,
            value="Test-creditor-id",
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM,
            value=False,
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_DUE_DAY,
            value=14,
        )

    def test_buildXmlString_default_returnsCorrectString(self):
        mock_timezone(
            test=self,
            now=datetime.datetime(
                year=2018, month=2, day=13, hour=12, minute=37, second=11, microsecond=1
            ),
        )

        payment_1 = PaymentFactory.build(amount=Decimal("75.20"), type="Test type")
        payment_2 = PaymentFactory.build(amount=Decimal("58.3"))

        result_string = Pain008XmlGenerator.build_xml_string(
            payments=[payment_1, payment_2],
            collection_date=datetime.date(year=2019, month=9, day=17),
            cache=self.cache,
        )

        tree = etree.XML(result_string)

        header = self._get_child("CstmrDrctDbtInitn/GrpHdr", tree)
        self.assertEqual(
            "Tapir-20180213123711000001",
            self._get_child("MsgId", header).text,
        )
        self.assertEqual(
            "2",
            self._get_child("NbOfTxs", header).text,
        )
        self.assertEqual(
            "133.50",
            self._get_child("CtrlSum", header).text,
        )
        self.assertEqual(
            "Test-site-name",
            self._get_child("InitgPty/Nm", header).text,
        )

        payment_information = self._get_child("CstmrDrctDbtInitn/PmtInf", tree)
        self.assertEqual(
            "Tapir-20180213123711000001",
            self._get_child("PmtInfId", payment_information).text,
        )
        self.assertEqual(
            "DD",
            self._get_child("PmtMtd", payment_information).text,
        )
        self.assertEqual(
            "2",
            self._get_child("NbOfTxs", payment_information).text,
        )
        self.assertEqual(
            "133.50",
            self._get_child("CtrlSum", payment_information).text,
        )
        self.assertEqual(
            "2019-09-14",
            self._get_child("ReqdColltnDt", payment_information).text,
        )
        self.assertEqual(
            "Test-site-name",
            self._get_child("Cdtr/Nm", payment_information).text,
        )
        self.assertEqual(
            "DE60500105172436256838",
            self._get_child("CdtrAcct/Id/IBAN", payment_information).text,
        )

        payment_type_information = self._get_child("PmtTpInf", payment_information)
        self.assertEqual(
            "SEPA",
            self._get_child("SvcLvl/Cd", payment_type_information).text,
        )
        self.assertEqual(
            "CORE",
            self._get_child("LclInstrm/Cd", payment_type_information).text,
        )
        self.assertEqual(
            "RCUR",
            self._get_child("SeqTp", payment_type_information).text,
        )

        payments = payment_information.findall("DrctDbtTxInf", namespaces=tree.nsmap)
        self.assertEqual(2, len(payments))

        first_payment = payments[0]
        self.assertEqual(
            "75.20",
            self._get_child("InstdAmt", first_payment).text,
        )
        self.assertEqual(
            payment_1.mandate_ref.ref,
            self._get_child("DrctDbtTx/MndtRltdInf/MndtId", first_payment).text,
        )
        self.assertEqual(
            payment_1.mandate_ref.member.iban,
            self._get_child("DbtrAcct/Id/IBAN", first_payment).text,
        )
        self.assertEqual(
            f"Test-site-name, {payment_1.mandate_ref.member.last_name}, Vertraege",
            self._get_child("RmtInf/Ustrd", first_payment).text,
        )

    @patch.object(PaymentExportIntendedUseBuilder, "build_intended_use", autospec=True)
    def test_buildXmlString_default_returnsCorrectlyConvertedSpecialCharacters(
        self, mock_build_intended_use: MagicMock
    ):
        mock_timezone(
            test=self,
            now=datetime.datetime(
                year=2018, month=2, day=13, hour=12, minute=37, second=11, microsecond=1
            ),
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM,
            value=True,
        )
        mock_build_intended_use.return_value = "Test type & Grün, \t\n René"

        payment_1 = PaymentFactory.build(
            amount=Decimal("75.20"),
            type="Test type & Grün",
            mandate_ref__member__first_name="Jörg",
            mandate_ref__member__last_name="René",
            subscription_payment_range_start=datetime.date(year=2019, month=9, day=17),
        )

        result_string = Pain008XmlGenerator.build_xml_string(
            payments=[payment_1],
            collection_date=datetime.date(year=2019, month=9, day=17),
            cache=self.cache,
        )

        tree = etree.XML(result_string)

        payment_information = self._get_child("CstmrDrctDbtInitn/PmtInf", tree)

        payments = payment_information.findall("DrctDbtTxInf", namespaces=tree.nsmap)
        self.assertEqual(1, len(payments))

        first_payment = payments[0]
        self.assertEqual(
            "Joerg Rene",
            self._get_child("Dbtr/Nm", first_payment).text,
        )
        self.assertEqual(
            f"Test type und Gruen, Rene",
            self._get_child("RmtInf/Ustrd", first_payment).text,
        )

    def test_buildXmlString_organizationIbanHasSpaces_exportContainsIbanWithoutSpaces(
        self,
    ):
        mock_timezone(
            test=self,
            now=datetime.datetime(
                year=2018, month=2, day=13, hour=12, minute=37, second=11, microsecond=1
            ),
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN,
            value="DE60 5001 0517 2436 2568 38",
        )

        payment_1 = PaymentFactory.build(amount=Decimal("75.20"), type="Test type")

        result_string = Pain008XmlGenerator.build_xml_string(
            payments=[payment_1],
            collection_date=datetime.date(year=2019, month=9, day=17),
            cache=self.cache,
        )

        tree = etree.XML(result_string)

        payment_information = self._get_child("CstmrDrctDbtInitn/PmtInf", tree)
        self.assertEqual(
            "DE60500105172436256838",
            self._get_child("CdtrAcct/Id/IBAN", payment_information).text,
        )

    def test_buildXmlString_bicNotSetInConfig_setsCreditorInstitutionIdToNotProvided(
        self,
    ):
        mock_timezone(
            test=self,
            now=datetime.datetime(
                year=2018, month=2, day=13, hour=12, minute=37, second=11, microsecond=1
            ),
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_ORGANISATION_BIC,
            value="",
        )

        payment_1 = PaymentFactory.build(amount=Decimal("75.20"), type="Test type")

        result_string = Pain008XmlGenerator.build_xml_string(
            payments=[payment_1],
            collection_date=datetime.date(year=2019, month=9, day=17),
            cache=self.cache,
        )

        tree = etree.XML(result_string)

        payment_information = self._get_child("CstmrDrctDbtInitn/PmtInf", tree)
        self.assertEqual(
            "NOTPROVIDED",
            self._get_child("CdtrAgt/FinInstnId/Othr/Id", payment_information).text,
        )

    def test_buildXmlString_bicSetInConfig_setsCreditorInstitutionIdToBic(
        self,
    ):
        mock_timezone(
            test=self,
            now=datetime.datetime(
                year=2018, month=2, day=13, hour=12, minute=37, second=11, microsecond=1
            ),
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_ORGANISATION_BIC,
            value="TESTBIC1234",
        )

        payment_1 = PaymentFactory.build(amount=Decimal("75.20"), type="Test type")

        result_string = Pain008XmlGenerator.build_xml_string(
            payments=[payment_1],
            collection_date=datetime.date(year=2019, month=9, day=17),
            cache=self.cache,
        )

        tree = etree.XML(result_string)

        payment_information = self._get_child("CstmrDrctDbtInitn/PmtInf", tree)
        self.assertEqual(
            "TESTBIC1234",
            self._get_child("CdtrAgt/FinInstnId/BICFI", payment_information).text,
        )

    def test_buildXmlString_invalidPayment_raisesGenericError(self):
        payment = PaymentFactory.build(amount=Decimal("-5"))

        with self.assertRaises(ValidationError):
            Pain008XmlGenerator.build_xml_string(
                payments=[payment],
                collection_date=datetime.date(year=2019, month=9, day=17),
                cache=self.cache,
            )

    def test_buildXmlString_missingOrgIban_raisesSpecificError(self):
        payment = PaymentFactory.build(amount=Decimal("10"))
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN,
            value="",
        )

        with self.assertRaises(ValidationError) as error:
            Pain008XmlGenerator.build_xml_string(
                payments=[payment],
                collection_date=datetime.date(year=2019, month=9, day=17),
                cache=self.cache,
            )

        self.assertIn(
            "Der Parameter 'IBAN der Organisation' muss in der Konfig gesetzt werden",
            error.exception.message,
        )

    def test_buildXmlString_missingOrgIdentifier_raisesSpecificError(self):
        payment = PaymentFactory.build(amount=Decimal("10"))
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER,
            value="",
        )

        with self.assertRaises(ValidationError) as error:
            Pain008XmlGenerator.build_xml_string(
                payments=[payment],
                collection_date=datetime.date(year=2019, month=9, day=17),
                cache=self.cache,
            )

        self.assertIn(
            "Der Parameter 'Gläubiger-Identifikationsnummer' muss in der Konfig gesetzt werden",
            error.exception.message,
        )

    def test_buildXmlString_invalidMemberIban_raisesSpecificError(self):
        payment = PaymentFactory.build(
            amount=Decimal("10"), mandate_ref__member__iban="INVALID"
        )

        with self.assertRaises(ValidationError) as error:
            Pain008XmlGenerator.build_xml_string(
                payments=[payment],
                collection_date=datetime.date(year=2019, month=9, day=17),
                cache=self.cache,
            )

        self.assertIn(
            "The value 'INVALID' is not accepted by the pattern",
            error.exception.message,
        )

    @classmethod
    def _get_child(cls, path: str, tree):
        current_node = tree
        for tag in path.split("/"):
            current_node = current_node.find(tag, namespaces=tree.nsmap)
        return current_node
