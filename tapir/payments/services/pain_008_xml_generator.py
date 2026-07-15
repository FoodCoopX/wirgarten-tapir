import datetime
from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ValidationError
from lxml import etree
from lxml.etree import Element

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_now


class Pain008XmlGenerator:
    # Generates payment files according to ISO20022 pain.008.001.08
    # A description of the format can be found here: https://developer.huntington.com/enterprisepayments/docs/iso-pain008
    # This PDF can also be used as reference: https://www.nacha.org/system/files/2023-12/NACHA_ISO20022_Guide_pain.008_direct_debit%208-9-23.pdf
    # search for the element names to get a definition of the fields in section "ISO 20022 File Format Table"
    # An updated version (pain.008.001.12) is available but this page https://www.gls.de/pain from the bank that most Tapir user use
    # says they user the .08 version.

    namespace = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.08"
    NOT_PROVIDED = "NOTPROVIDED"

    @classmethod
    def build_xml_string(
        cls, payments: list[Payment], cache: dict, collection_date: datetime.date
    ):
        if len(payments) > 1:
            for payment in payments:
                cls.validate_single_payment(
                    payment=payment, cache=cache, collection_date=collection_date
                )

        namespace_map = {
            None: cls.namespace,
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }
        document = cls._create_element("Document", nsmap=namespace_map)

        document.set(
            etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation"),
            f"{cls.namespace} pain.008.001.08.xsd",
        )

        container = cls._append_element(document, "CstmrDrctDbtInitn")

        document_id = cls._get_document_id(get_now(cache=cache))
        container.append(
            cls._build_global_header(
                payments=payments, cache=cache, document_id=document_id
            )
        )
        container.append(
            cls._build_payments(
                payments=payments,
                cache=cache,
                document_id=document_id,
                collection_date=collection_date,
            )
        )

        errors = cls._validate_document(document)
        if len(errors) > 0:
            raise ValidationError(", ".join(errors))

        return etree.tostring(document, pretty_print=True, xml_declaration=True)

    @classmethod
    def validate_single_payment(
        cls, payment: Payment, cache: dict, collection_date: datetime.date
    ):
        try:
            cls.build_xml_string(
                payments=[payment], cache=cache, collection_date=collection_date
            )
        except ValidationError as error:
            raise ValidationError(
                f"Error when building XML for payment: {payment}: {error}"
            )

    @classmethod
    def _build_payments(
        cls,
        cache: dict,
        payments: list[Payment],
        document_id: str,
        collection_date: datetime.date,
    ):
        payments_container = cls._create_element("PmtInf")

        cls._add_payments_header(
            cache=cache,
            payments=payments,
            payments_container=payments_container,
            document_id=document_id,
            collection_date=collection_date,
        )

        for payment in payments:
            cls._add_payment(
                payments_container=payments_container, payment=payment, cache=cache
            )

        return payments_container

    @classmethod
    def _add_payment(cls, payments_container, payment: Payment, cache: dict):
        direct_debit_transaction_info = cls._append_element(
            payments_container, "DrctDbtTxInf"
        )

        payment_id = cls._append_element(direct_debit_transaction_info, "PmtId")
        end_to_end_id = cls._append_element(payment_id, "EndToEndId")
        end_to_end_id.text = cls.NOT_PROVIDED

        instructed_amount = cls._append_element(
            direct_debit_transaction_info, "InstdAmt"
        )
        instructed_amount.set("Ccy", "EUR")
        instructed_amount.text = cls._format_currency(payment.amount)

        direct_debit_transaction = cls._append_element(
            direct_debit_transaction_info, "DrctDbtTx"
        )
        mandate_related_information = cls._append_element(
            direct_debit_transaction, "MndtRltdInf"
        )
        mandate_id = cls._append_element(mandate_related_information, "MndtId")
        mandate_id.text = payment.mandate_ref.ref
        date_of_signature = cls._append_element(
            mandate_related_information, "DtOfSgntr"
        )
        date_of_signature.text = cls._format_date(payment.mandate_ref.start_ts.date())

        debitor_agent = cls._append_element(direct_debit_transaction_info, "DbtrAgt")
        debitor_institution_id = cls._append_element(debitor_agent, "FinInstnId")
        debitor_institution_other = cls._append_element(debitor_institution_id, "Othr")
        debitor_institution_other_id = cls._append_element(
            debitor_institution_other, "Id"
        )
        debitor_institution_other_id.text = cls.NOT_PROVIDED

        debitor = cls._append_element(direct_debit_transaction_info, "Dbtr")
        debitor_name = cls._append_element(debitor, "Nm")
        debitor_name.text = f"{payment.mandate_ref.member.first_name} {payment.mandate_ref.member.last_name}"

        debitor_account = cls._append_element(direct_debit_transaction_info, "DbtrAcct")
        debitor_account_id = cls._append_element(debitor_account, "Id")
        debitor_iban = cls._append_element(debitor_account_id, "IBAN")
        debitor_iban.text = payment.mandate_ref.member.iban

        remittance_information = cls._append_element(
            direct_debit_transaction_info, "RmtInf"
        )
        unstructured = cls._append_element(remittance_information, "Ustrd")
        unstructured.text = PaymentExportIntendedUseBuilder.build_intended_use(
            payment=payment,
            is_contracts=payment.type != PAYMENT_TYPE_COOP_SHARES,
            cache=cache,
        )

    @classmethod
    def _add_payments_header(
        cls,
        cache: dict,
        payments_container,
        payments: list[Payment],
        document_id: str,
        collection_date: datetime.date,
    ):
        payment_id = cls._append_element(payments_container, "PmtInfId")
        payment_id.text = document_id

        payment_method = cls._append_element(payments_container, "PmtMtd")
        payment_method.text = "DD"

        number_of_transactions = cls._append_element(payments_container, "NbOfTxs")
        number_of_transactions.text = str(len(payments))

        control_sum_element = cls._append_element(payments_container, "CtrlSum")
        control_sum_element.text = cls._get_control_sum(payments)

        payment_type_information = cls._append_element(payments_container, "PmtTpInf")

        service_level = cls._append_element(payment_type_information, "SvcLvl")
        service_code = cls._append_element(service_level, "Cd")
        service_code.text = "SEPA"
        local_instrument = cls._append_element(payment_type_information, "LclInstrm")
        instrument_code = cls._append_element(local_instrument, "Cd")
        instrument_code.text = "CORE"
        sequence_type = cls._append_element(payment_type_information, "SeqTp")
        sequence_type.text = "RCUR"

        requested_collection_date = cls._append_element(
            payments_container, "ReqdColltnDt"
        )
        requested_collection_date.text = cls._format_date(collection_date)

        creditor = cls._append_element(payments_container, "Cdtr")
        creditor_name = cls._append_element(creditor, "Nm")
        creditor_name.text = get_parameter_value(
            key=ParameterKeys.SITE_NAME, cache=cache
        )

        creditor_account = cls._append_element(payments_container, "CdtrAcct")
        creditor_id = cls._append_element(creditor_account, "Id")
        creditor_iban = cls._append_element(creditor_id, "IBAN")
        creditor_iban.text = get_parameter_value(
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN, cache=cache
        )
        if len(creditor_iban.text.strip()) == 0:
            raise ValidationError(
                "Der Parameter 'IBAN der Organisation' muss in der Konfig gesetzt werden"
            )

        creditor_agent = cls._append_element(payments_container, "CdtrAgt")
        financial_institution_id_container = cls._append_element(
            creditor_agent, "FinInstnId"
        )
        financial_instituion_other = cls._append_element(
            financial_institution_id_container, "Othr"
        )
        financial_institution_id = cls._append_element(financial_instituion_other, "Id")
        financial_institution_id.text = cls.NOT_PROVIDED

        chrg_br = cls._append_element(
            payments_container, "ChrgBr"
        )  # could not find what this one means
        chrg_br.text = "SLEV"

        creditor_scheme = cls._append_element(payments_container, "CdtrSchmeId")
        creditor_scheme_id = cls._append_element(creditor_scheme, "Id")
        creditor_private_identification = cls._append_element(
            creditor_scheme_id, "PrvtId"
        )
        creditor_other = cls._append_element(creditor_private_identification, "Othr")
        creditor_id = cls._append_element(creditor_other, "Id")
        creditor_id.text = get_parameter_value(
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, cache=cache
        )
        if len(creditor_id.text.strip()) == 0:
            raise ValidationError(
                "Der Parameter 'Gläubiger-Identifikationsnummer' muss in der Konfig gesetzt werden"
            )
        creditor_scheme_name = cls._append_element(creditor_other, "SchmeNm")
        creditor_scheme_proprietary = cls._append_element(creditor_scheme_name, "Prtry")
        creditor_scheme_proprietary.text = "SEPA"

    @classmethod
    def _build_global_header(
        cls, cache: dict, payments: list[Payment], document_id: str
    ):
        header = cls._create_element("GrpHdr")

        message_id = cls._append_element(header, "MsgId")
        message_id.text = document_id

        timestamp = cls._append_element(header, "CreDtTm")
        timestamp.text = get_now(cache=cache).isoformat()

        number_of_transactions = cls._append_element(header, "NbOfTxs")
        number_of_transactions.text = str(len(payments))

        control_sum_element = cls._append_element(header, "CtrlSum")
        control_sum_element.text = cls._get_control_sum(payments)

        initiator = cls._append_element(header, "InitgPty")
        name = cls._append_element(initiator, "Nm")
        name.text = get_parameter_value(key=ParameterKeys.SITE_NAME, cache=cache)

        return header

    @classmethod
    def _validate_document(cls, document: Element) -> list[str]:
        path = Path(__file__).with_name("pain.008.001.08.xsd")
        with path.open("rb") as file:
            schema_root = etree.XML(file.read())

        schema = etree.XMLSchema(schema_root)

        if schema.validate(document):
            return []

        return [error.message for error in schema.error_log]

    @classmethod
    def _get_document_id(cls, timestamp: datetime.datetime):
        return f"Tapir-{timestamp.strftime('%Y%m%d%H%M%S%f')}"

    @classmethod
    def _get_control_sum(cls, payments: list[Payment]):
        control_sum = sum([payment.amount for payment in payments], start=Decimal(0))
        return cls._format_currency(control_sum)

    @classmethod
    def _format_currency(cls, amount: Decimal):
        return f"{amount:.2f}"

    @classmethod
    def _format_date(cls, date: datetime.date):
        return date.strftime("%Y-%m-%d")

    @classmethod
    def _create_element(cls, tag, **kwargs):
        return etree.Element(f"{{{cls.namespace}}}{tag}", **kwargs)

    @classmethod
    def _append_element(cls, parent, tag, **kwargs):
        return etree.SubElement(parent, f"{{{cls.namespace}}}{tag}", **kwargs)
