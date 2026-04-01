import datetime
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_SKIPPED,
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_UPDATED,
)
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.wirgarten.models import Member, CoopShareTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.wirgarten.utils import get_today


class ShareImporter:
    @classmethod
    def import_shares_single_member(cls, row: dict[str, str], update_existing: bool):
        if DataImportUtils.is_row_empty(row):
            return None

        # {'Mitgliedsnummer': '1', 'Bewegungsart (Z,Ü,K)': 'Z', 'Datum': '2017-03-10', 'Anzahl Anteile': '2', 'Wert Anteile': '100', 'Übertragungspartner': '', 'Wirkung Kündigung': ''}

        number_of_shares = DataImportUtils.safe_int(row.get("Anzahl Anteile"))
        transfer_member = None
        transaction_valid_at = DataImportUtils.to_date(row.get("Datum"))
        member_no = DataImportUtils.normalize_cell(row.get("Mitgliedsnummer"))

        try:
            member = Member.objects.get(member_no=member_no)
        except ObjectDoesNotExist:
            raise TapirDataImportException(
                f"Database Error: Member with number {member_no} not found"
            )

        if DataImportUtils.normalize_cell(row.get("Übertragungspartner")) != "":
            try:
                transfer_member = Member.objects.get(
                    member_no=DataImportUtils.normalize_cell(
                        row.get("Übertragungspartner")
                    )
                )
            except ObjectDoesNotExist:
                raise TapirDataImportException("Transfer Member not found!")

        transaction_type, transaction_valid_at = cls.get_share_transaction_type(
            number_of_shares=number_of_shares,
            row=row,
            transaction_valid_at=transaction_valid_at,
        )

        existing_transaction = CoopShareTransaction.objects.filter(
            member=member,
            transaction_type=transaction_type,
            valid_at=transaction_valid_at,
            transfer_member=transfer_member,
        ).first()

        if existing_transaction:
            if not update_existing:
                return MEMBER_IMPORT_STATUS_SKIPPED

            return cls.update_existing_transaction(
                existing_transaction=existing_transaction,
                number_of_shares=number_of_shares,
                valid_date=transaction_valid_at,
            )

        transaction = CoopShareTransaction.objects.create(
            member_id=member.id,
            transaction_type=transaction_type,
            valid_at=transaction_valid_at,
            quantity=number_of_shares,
            share_price=get_parameter_value(
                key=ParameterKeys.COOP_SHARE_PRICE, cache={}
            ),
            transfer_member=transfer_member,
            mandate_ref=get_or_create_mandate_ref(member),
        )

        cls.create_or_update_payment_if_necessary(transaction)

        return MEMBER_IMPORT_STATUS_CREATED

    @classmethod
    def get_share_transaction_type(
        cls,
        number_of_shares: int,
        row: dict[str, str],
        transaction_valid_at: datetime.date,
    ) -> tuple[CoopShareTransaction.CoopShareTransactionType, datetime.date]:
        transaction_type_key = DataImportUtils.normalize_cell(
            row.get("Bewegungsart (Z,Ü,K)")
        )

        match transaction_type_key:
            case "Z":
                return (
                    CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                    transaction_valid_at,
                )
            case "Ü":
                if number_of_shares > 0:
                    transaction_type = (
                        CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN
                    )
                else:
                    transaction_type = (
                        CoopShareTransaction.CoopShareTransactionType.TRANSFER_OUT
                    )
                return transaction_type, transaction_valid_at
            case "K":
                transaction_type = (
                    CoopShareTransaction.CoopShareTransactionType.CANCELLATION
                )
                transaction_valid_at = DataImportUtils.to_date(
                    row.get("Wirkung Kündigung")
                )
                return transaction_type, transaction_valid_at
            case _:
                raise ValueError(f"Unknown transaction type: '{transaction_type_key}'")

    @classmethod
    def update_existing_transaction(
        cls,
        existing_transaction: CoopShareTransaction,
        number_of_shares: int,
        valid_date: datetime.date,
    ) -> str:
        is_updated = False

        if DataImportUtils.update_if_diff(
            existing_transaction, "quantity", number_of_shares
        ):
            is_updated = True
        if DataImportUtils.update_if_diff(existing_transaction, "valid_at", valid_date):
            is_updated = True
        mandate_ref = get_or_create_mandate_ref(existing_transaction.member)
        if DataImportUtils.update_if_diff(
            existing_transaction, "mandate_ref", mandate_ref
        ):
            is_updated = True

        share_price = Decimal(
            get_parameter_value(key=ParameterKeys.COOP_SHARE_PRICE, cache={})
        )
        if DataImportUtils.update_if_diff(
            existing_transaction, "share_price", share_price
        ):
            is_updated = True

        if cls.create_or_update_payment_if_necessary(existing_transaction):
            is_updated = True

        if not is_updated:
            return MEMBER_IMPORT_STATUS_SKIPPED

        try:
            existing_transaction.save()
            return MEMBER_IMPORT_STATUS_UPDATED
        except Exception as e:
            raise TapirDataImportException(
                f"Error updating share transaction (member: {existing_transaction.member}): {e}"
            )

    @classmethod
    def create_or_update_payment_if_necessary(cls, transaction: CoopShareTransaction):
        if (
            transaction.transaction_type
            != CoopShareTransaction.CoopShareTransactionType.PURCHASE
        ):
            return False

        should_have_a_payment = transaction.valid_at >= get_today()

        if not should_have_a_payment:
            if transaction.payment is None:
                return False

            cls.delete_payment(transaction)
            return True

        if transaction.payment is None:
            payment = CoopSharePurchaseHandler.create_or_update_payment(
                shares_valid_at=transaction.valid_at,
                mandate_ref=transaction.mandate_ref,
                quantity=transaction.quantity,
                cache={},
            )
            transaction.payment = payment
            transaction.save()
            return True

        payment = transaction.payment
        updated = False

        due_date = CoopSharePurchaseHandler.get_payment_due_date(
            shares_valid_at=transaction.valid_at, cache={}
        )
        if DataImportUtils.update_if_diff(payment, "due_date", due_date):
            updated = True

        amount = transaction.share_price * transaction.quantity
        if DataImportUtils.update_if_diff(payment, "amount", amount):
            updated = True

        return updated

    @classmethod
    def delete_payment(cls, transaction: CoopShareTransaction):
        payment = transaction.payment
        transaction.payment = None
        transaction.save()
        payment.delete()
