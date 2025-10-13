from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.member_credit_creator import MemberCreditCreator


class TestCreateMemberCreditIfNecessary(SimpleTestCase):
    @patch.object(MemberCreditCreator, "create_credit_and_log_entry")
    @patch.object(MemberCreditCreator, "get_amount_to_credit")
    def test_createMemberCreditIfNecessary_amountToCreditIsZero_doesntCreateCredit(
        self, mock_get_amount_to_credit: Mock, mock_create_credit_and_log_entry: Mock
    ):
        mock_get_amount_to_credit.return_value = 0
        member = Mock()
        product_type = Mock()
        reference_date = Mock()
        comment = Mock()
        cache = Mock()
        actor = Mock()

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            product_type=product_type,
            reference_date=reference_date,
            comment=comment,
            cache=cache,
            actor=actor,
        )

        mock_get_amount_to_credit.assert_called_once_with(
            member=member,
            product_type=product_type,
            reference_date=reference_date,
            cache=cache,
        )
        mock_create_credit_and_log_entry.assert_not_called()

    @patch.object(MemberCreditCreator, "create_credit_and_log_entry")
    @patch.object(MemberCreditCreator, "get_amount_to_credit")
    def test_createMemberCreditIfNecessary_amountToCreditIsAboveZero_createsCredit(
        self, mock_get_amount_to_credit: Mock, mock_create_credit_and_log_entry: Mock
    ):
        mock_get_amount_to_credit.return_value = 0.01
        member = Mock()
        product_type = Mock()
        reference_date = Mock()
        comment = Mock()
        cache = Mock()
        actor = Mock()

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            product_type=product_type,
            reference_date=reference_date,
            comment=comment,
            cache=cache,
            actor=actor,
        )

        mock_get_amount_to_credit.assert_called_once_with(
            member=member,
            product_type=product_type,
            reference_date=reference_date,
            cache=cache,
        )
        mock_create_credit_and_log_entry.assert_called_once_with(
            member=member,
            actor=actor,
            amount_to_credit=0.01,
            reference_date=reference_date,
            comment=comment,
        )
