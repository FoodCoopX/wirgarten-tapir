import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestBuyCooperativeShares(SimpleTestCase):
    @patch("tapir.coop.services.coop_share_purchase_handler.get_parameter_value")
    @patch.object(CoopSharePurchaseHandler, "send_warning_mail_if_necessary")
    @patch.object(CoopShareTransaction, "objects")
    @patch.object(CoopSharePurchaseHandler, "create_or_update_payment")
    @patch("tapir.coop.services.coop_share_purchase_handler.get_or_create_mandate_ref")
    def test_buyCooperativeShares_default_createPaymentAndSharesAndSendsMail(
        self,
        mock_get_or_create_mandate_ref: Mock,
        mock_create_or_update_payment: Mock,
        mock_coop_share_transaction_objects: Mock,
        mock_send_warning_mail_if_necessary: Mock,
        mock_get_parameter_value: Mock,
    ):
        now = datetime.datetime(year=2024, month=1, day=17)
        now = mock_timezone(self, now)
        member = Mock()
        member.sepa_consent = now - datetime.timedelta(hours=1)
        shares_valid_at = datetime.date(year=2024, month=2, day=13)
        cache = {}
        mandate_ref = Mock()
        mock_get_or_create_mandate_ref.return_value = mandate_ref
        payment = Mock()
        mock_create_or_update_payment.return_value = payment
        transaction = Mock()
        mock_coop_share_transaction_objects.create.return_value = transaction
        mock_get_parameter_value.return_value = 75

        result = CoopSharePurchaseHandler.buy_cooperative_shares(
            quantity=12, member=member, shares_valid_at=shares_valid_at, cache=cache
        )

        mock_get_or_create_mandate_ref.assert_called_once_with(
            member=member, cache=cache
        )
        mock_create_or_update_payment.assert_called_once_with(
            shares_valid_at=shares_valid_at,
            mandate_ref=mandate_ref,
            quantity=12,
            cache=cache,
        )
        mock_coop_share_transaction_objects.create.assert_called_once_with(
            member=member,
            quantity=12,
            share_price=75,
            valid_at=shares_valid_at,
            mandate_ref=mandate_ref,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            payment=payment,
        )
        self.assertEqual(now, member.sepa_consent)
        member.save.assert_called_once_with(cache=cache)
        mock_send_warning_mail_if_necessary.assert_called_once_with(
            quantity=12, shares_valid_at=shares_valid_at, member=member, cache=cache
        )
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.COOP_SHARE_PRICE, cache=cache
        )

        self.assertEqual(result, transaction)

    @patch("tapir.coop.services.coop_share_purchase_handler.get_parameter_value")
    @patch.object(CoopSharePurchaseHandler, "send_warning_mail_if_necessary")
    @patch.object(CoopShareTransaction, "objects")
    @patch.object(CoopSharePurchaseHandler, "create_or_update_payment")
    @patch("tapir.coop.services.coop_share_purchase_handler.get_or_create_mandate_ref")
    def test_buyCooperativeShares_memberSepaConsentIsAlreadySetToNow_dontSaveMember(
        self,
        mock_get_or_create_mandate_ref: Mock,
        mock_create_or_update_payment: Mock,
        mock_coop_share_transaction_objects: Mock,
        mock_send_warning_mail_if_necessary: Mock,
        mock_get_parameter_value: Mock,
    ):
        now = datetime.datetime(year=2024, month=1, day=17)
        now = mock_timezone(self, now)
        member = Mock()
        member.sepa_consent = now
        shares_valid_at = datetime.date(year=2024, month=2, day=13)
        cache = {}
        mandate_ref = Mock()
        mock_get_or_create_mandate_ref.return_value = mandate_ref
        payment = Mock()
        mock_create_or_update_payment.return_value = payment
        transaction = Mock()
        mock_coop_share_transaction_objects.create.return_value = transaction
        mock_get_parameter_value.return_value = 75

        result = CoopSharePurchaseHandler.buy_cooperative_shares(
            quantity=12, member=member, shares_valid_at=shares_valid_at, cache=cache
        )

        mock_get_or_create_mandate_ref.assert_called_once_with(
            member=member, cache=cache
        )
        mock_create_or_update_payment.assert_called_once_with(
            shares_valid_at=shares_valid_at,
            mandate_ref=mandate_ref,
            quantity=12,
            cache=cache,
        )
        mock_coop_share_transaction_objects.create.assert_called_once_with(
            member=member,
            quantity=12,
            share_price=75,
            valid_at=shares_valid_at,
            mandate_ref=mandate_ref,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            payment=payment,
        )
        member.save.assert_not_called()
        mock_send_warning_mail_if_necessary.assert_called_once_with(
            quantity=12, shares_valid_at=shares_valid_at, member=member, cache=cache
        )
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.COOP_SHARE_PRICE, cache=cache
        )

        self.assertEqual(result, transaction)
