import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.subscription_update_view_change_applier import (
    SubscriptionUpdateViewChangeApplier,
)
from tapir.wirgarten.tests.test_utils import mock_timezone


@patch.object(MemberCreditCreator, "create_member_credit_if_necessary", autospec=True)
@patch.object(
    SubscriptionUpdateViewChangeApplier,
    "change_payment_rhythm_if_necessary",
    autospec=True,
)
@patch.object(ApplyTapirOrderManager, "send_order_confirmation_mail", autospec=True)
@patch.object(ApplyTapirOrderManager, "apply_order_single_product_type", autospec=True)
@patch.object(
    MemberPickupLocationSetter, "link_member_to_pickup_location", autospec=True
)
@patch.object(
    MemberPickupLocationGetter, "get_member_pickup_location_id", autospec=True
)
class TestSubscriptionUpdateViewChangeApplierApplyChanges(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2027, month=12, day=20)
        )

    def test_applyChanges_desiredPickupLocationIsDifferentFromCurrent_setLocationToDesired(
        self,
        mock_get_member_pickup_location_id: Mock,
        mock_link_member_to_pickup_location: Mock,
        mock_apply_order_single_product_type: Mock,
        *other_mocks
    ):
        contract_start_date = Mock()
        mock_get_member_pickup_location_id.return_value = "current_id"
        member = Mock()
        actor = Mock()
        cache = Mock()
        subscriptions_existed_before_changes = Mock()
        new_subscriptions = Mock()
        mock_apply_order_single_product_type.return_value = (
            subscriptions_existed_before_changes,
            new_subscriptions,
        )

        SubscriptionUpdateViewChangeApplier.apply_changes(
            member=member,
            product_type=Mock(),
            contract_start_date=contract_start_date,
            actor=actor,
            desired_pickup_location_id="desired_id",
            order=Mock(),
            payment_rhythm=Mock(),
            iban="test_iban",
            account_owner="test_account_owner",
            sepa_allowed=True,
            cache=cache,
        )

        mock_get_member_pickup_location_id.assert_called_once_with(
            member=member, reference_date=contract_start_date
        )
        mock_link_member_to_pickup_location.assert_called_once_with(
            member=member,
            valid_from=contract_start_date,
            pickup_location_id="desired_id",
            actor=actor,
            cache=cache,
        )
        mock_apply_order_single_product_type.assert_called_once()
        for mock in other_mocks:
            mock.assert_called_once()

    def test_applyChanges_desiredPickupLocationIsSameAsCurrent_dontSetPickupLocation(
        self,
        mock_get_member_pickup_location_id: Mock,
        mock_link_member_to_pickup_location: Mock,
        mock_apply_order_single_product_type: Mock,
        *other_mocks
    ):
        contract_start_date = Mock()
        mock_get_member_pickup_location_id.return_value = "same_id"
        member = Mock()
        actor = Mock()
        cache = Mock()
        subscriptions_existed_before_changes = Mock()
        new_subscriptions = Mock()
        mock_apply_order_single_product_type.return_value = (
            subscriptions_existed_before_changes,
            new_subscriptions,
        )

        SubscriptionUpdateViewChangeApplier.apply_changes(
            member=member,
            product_type=Mock(),
            contract_start_date=contract_start_date,
            actor=actor,
            desired_pickup_location_id="same_id",
            order=Mock(),
            payment_rhythm=Mock(),
            iban="test_iban",
            account_owner="test_account_owner",
            sepa_allowed=True,
            cache=cache,
        )

        mock_get_member_pickup_location_id.assert_called_once_with(
            member=member, reference_date=contract_start_date
        )
        mock_link_member_to_pickup_location.assert_not_called()
        mock_apply_order_single_product_type.assert_called_once()
        for mock in other_mocks:
            mock.assert_called_once()

    def test_applyChanges_default_callsAllServicesCorrectlyAndSavesMemberWithNewBankData(
        self,
        mock_get_member_pickup_location_id: Mock,
        mock_link_member_to_pickup_location: Mock,
        mock_apply_order_single_product_type: Mock,
        mock_send_order_confirmation_mail: Mock,
        mock_change_payment_rhythm_if_necessary: Mock,
        mock_create_member_credit_if_necessary: Mock,
    ):
        contract_start_date = Mock()
        mock_get_member_pickup_location_id.return_value = "same_id"
        member = Mock()
        actor = Mock()
        cache = Mock()
        order = Mock()
        product_type = Mock()
        payment_rhythm = Mock()
        subscriptions_existed_before_changes = Mock()
        new_subscriptions = Mock()
        mock_apply_order_single_product_type.return_value = (
            subscriptions_existed_before_changes,
            new_subscriptions,
        )

        SubscriptionUpdateViewChangeApplier.apply_changes(
            member=member,
            product_type=product_type,
            contract_start_date=contract_start_date,
            actor=actor,
            desired_pickup_location_id="same_id",
            order=order,
            payment_rhythm=payment_rhythm,
            iban="test_iban",
            account_owner="test_account_owner",
            sepa_allowed=True,
            cache=cache,
        )

        mock_get_member_pickup_location_id.assert_called_once_with(
            member=member, reference_date=contract_start_date
        )
        mock_link_member_to_pickup_location.assert_not_called()
        mock_apply_order_single_product_type.assert_called_once_with(
            member=member,
            order=order,
            contract_start_date=contract_start_date,
            product_type=product_type,
            actor=actor,
            needs_admin_confirmation=True,
            cache=cache,
        )
        mock_send_order_confirmation_mail.assert_called_once_with(
            subscriptions_existed_before_changes=subscriptions_existed_before_changes,
            member=member,
            new_subscriptions=new_subscriptions,
            cache=cache,
            from_waiting_list=False,
            solidarity_contribution=None,
        )
        mock_change_payment_rhythm_if_necessary.assert_called_once_with(
            payment_rhythm=payment_rhythm, member=member, actor=actor, cache=cache
        )
        mock_create_member_credit_if_necessary.assert_called_once_with(
            member=member,
            actor=actor,
            product_type_id_or_soli=product_type.id,
            reference_date=contract_start_date,
            comment="Produkt-Anteil vom Admin durch dem Mitgliederbereich reduziert",
            cache=cache,
        )

        self.assertEqual("test_iban", member.iban)
        self.assertEqual("test_account_owner", member.account_owner)
        self.assertEqual(self.now, member.sepa_consent)

        member.save.assert_called_once_with()

    def test_applyChanges_bankDataNotSet_memberBankDataNotChanged(
        self,
        mock_get_member_pickup_location_id: Mock,
        mock_link_member_to_pickup_location: Mock,
        mock_apply_order_single_product_type: Mock,
        *other_mocks
    ):
        member = Mock(
            iban="original_iban",
            account_owner="original_account_owner",
            sepa_consent=None,
        )

        subscriptions_existed_before_changes = Mock()
        new_subscriptions = Mock()
        mock_apply_order_single_product_type.return_value = (
            subscriptions_existed_before_changes,
            new_subscriptions,
        )

        SubscriptionUpdateViewChangeApplier.apply_changes(
            member=member,
            product_type=Mock(),
            contract_start_date=Mock(),
            actor=Mock(),
            desired_pickup_location_id=Mock(),
            order=Mock(),
            payment_rhythm=Mock(),
            iban="",
            account_owner="",
            sepa_allowed=False,
            cache=Mock(),
        )

        all_mocks = [
            mock_get_member_pickup_location_id,
            mock_link_member_to_pickup_location,
            mock_apply_order_single_product_type,
            *other_mocks,
        ]
        for mock in all_mocks:
            mock.assert_called_once()

        self.assertEqual("original_iban", member.iban)
        self.assertEqual("original_account_owner", member.account_owner)
        self.assertIsNone(member.sepa_consent)

        member.save.assert_called_once_with()
