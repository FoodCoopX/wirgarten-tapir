import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from lxml import etree

from tapir.payments.services.pain_008_xml_generator import Pain008XmlGenerator
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
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER,
            value="Test-creditor-id",
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM,
            value=False,
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
            "2019-09-17",
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
            "NOTPROVIDED",
            self._get_child("PmtId/EndToEndId", first_payment).text,
        )
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
            f"Test-site-name, {payment_1.mandate_ref.member.last_name}, Verträge",
            self._get_child("RmtInf/Ustrd", first_payment).text,
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
