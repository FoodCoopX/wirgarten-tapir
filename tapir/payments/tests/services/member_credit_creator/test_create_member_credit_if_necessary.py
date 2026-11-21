from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.payments.dataclasses import CreditCalculation
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCreateMemberCreditIfNecessary(TapirUnitTest):
    @patch.object(MemberCreditCreator, "create_credit_and_log_entry", autospec=True)
    @patch.object(MemberCreditCreator, "get_credit_calculation", autospec=True)
    def test_createMemberCreditIfNecessary_amountToCreditIsZero_doesntCreateCredit(
        self, mock_get_credit_calculation: Mock, mock_create_credit_and_log_entry: Mock
    ):
        mock_get_credit_calculation.return_value = CreditCalculation(
            amount=Decimal(0), explanation=""
        )
        member = Mock()
        product_type = Mock()
        reference_date = Mock()
        comment = Mock()
        cache = Mock()
        actor = Mock()

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            product_type_id_or_soli=product_type.id,
            reference_date=reference_date,
            comment=comment,
            cache=cache,
            actor=actor,
        )

        mock_get_credit_calculation.assert_called_once_with(
            member=member,
            product_type_id_or_soli=product_type.id,
            reference_date=reference_date,
            cache=cache,
        )
        mock_create_credit_and_log_entry.assert_not_called()

    @patch.object(MemberCreditCreator, "create_credit_and_log_entry", autospec=True)
    @patch.object(MemberCreditCreator, "get_credit_calculation", autospec=True)
    def test_createMemberCreditIfNecessary_amountToCreditIsAboveZero_createsCredit(
        self, mock_get_credit_calculation: Mock, mock_create_credit_and_log_entry: Mock
    ):
        mock_get_credit_calculation.return_value = CreditCalculation(
            amount=Decimal("0.01"), explanation="Berechnung"
        )
        member = Mock()
        product_type = Mock()
        reference_date = Mock()
        comment = "Produkt-Anteil vom Admin reduziert"
        cache = Mock()
        actor = Mock()

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            product_type_id_or_soli=product_type.id,
            reference_date=reference_date,
            comment=comment,
            cache=cache,
            actor=actor,
        )

        mock_get_credit_calculation.assert_called_once_with(
            member=member,
            product_type_id_or_soli=product_type.id,
            reference_date=reference_date,
            cache=cache,
        )
        mock_create_credit_and_log_entry.assert_called_once_with(
            member=member,
            actor=actor,
            amount_to_credit=Decimal("0.01"),
            reference_date=reference_date,
            comment="Produkt-Anteil vom Admin reduziert\nBerechnung",
            product_type_id_or_soli=product_type.id,
            cache=cache,
        )
