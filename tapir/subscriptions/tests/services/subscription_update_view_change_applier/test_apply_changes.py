from unittest.mock import patch, Mock, MagicMock, call

from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.contract_prerequisites_applier import (
    ContractPrerequisitesApplier,
)
from tapir.subscriptions.services.subscription_update_view_change_applier import (
    SubscriptionUpdateViewChangeApplier,
)
from tapir.wirgarten.tests.factories import MemberFactory, ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestSubscriptionUpdateViewChangeApplierApplyChanges(TapirUnitTest):
    @patch.object(ContractPrerequisitesApplier, "apply_banking_data", autospec=True)
    @patch.object(
        MemberCreditCreator, "create_member_credit_if_necessary", autospec=True
    )
    @patch.object(ApplyTapirOrderManager, "send_order_confirmation_mail", autospec=True)
    @patch.object(
        ApplyTapirOrderManager,
        "apply_order_single_product_type",
        autospec=True,
        return_value=(True, []),
    )
    @patch.object(
        ContractPrerequisitesApplier,
        "change_payment_rhythm_if_necessary",
        autospec=True,
    )
    @patch.object(ContractPrerequisitesApplier, "apply_pickup_location", autospec=True)
    def test_applyChanges_default_callsAllServicesInOrder(
        self,
        mock_apply_pickup_location: MagicMock,
        mock_change_payment_rhythm_if_necessary: MagicMock,
        mock_apply_order_single_product_type: MagicMock,
        mock_send_order_confirmation_mail: MagicMock,
        mock_create_member_credit_if_necessary: MagicMock,
        mock_apply_banking_data: MagicMock,
    ):
        manager = Mock()
        manager.attach_mock(mock_apply_pickup_location, "apply_pickup_location")
        manager.attach_mock(
            mock_change_payment_rhythm_if_necessary, "change_payment_rhythm"
        )
        manager.attach_mock(mock_apply_order_single_product_type, "apply_order")
        manager.attach_mock(mock_send_order_confirmation_mail, "send_mail")
        manager.attach_mock(mock_create_member_credit_if_necessary, "create_credit")
        manager.attach_mock(mock_apply_banking_data, "apply_banking_data")
        member = MemberFactory.build()
        product_type = ProductTypeFactory.build()
        contract_start_date = Mock()
        actor = Mock()
        order = Mock()
        cache = {}

        SubscriptionUpdateViewChangeApplier.apply_changes(
            member=member,
            product_type=product_type,
            contract_start_date=contract_start_date,
            actor=actor,
            desired_pickup_location_id="desired_id",
            order=order,
            payment_rhythm="yearly",
            iban="test_iban",
            account_owner="test_account_owner",
            sepa_allowed=True,
            cache=cache,
        )

        self.assertEqual(
            [
                call.apply_pickup_location(
                    member=member,
                    contract_start_date=contract_start_date,
                    desired_pickup_location_id="desired_id",
                    actor=actor,
                    cache=cache,
                ),
                call.change_payment_rhythm(
                    payment_rhythm="yearly", member=member, actor=actor, cache=cache
                ),
                call.apply_order(
                    member=member,
                    order=order,
                    contract_start_date=contract_start_date,
                    product_type=product_type,
                    actor=actor,
                    needs_admin_confirmation=True,
                    cache=cache,
                ),
                call.send_mail(
                    subscriptions_existed_before_changes=True,
                    member=member,
                    new_subscriptions=[],
                    cache=cache,
                    from_waiting_list=False,
                    coop_share_transaction=None,
                    association_membership=None,
                    solidarity_contribution=None,
                ),
                call.create_credit(
                    member=member,
                    actor=actor,
                    product_type_id_or_soli=product_type.id,
                    reference_date=contract_start_date,
                    comment="Produkt-Anteil vom Admin durch dem Mitgliederbereich reduziert",
                    cache=cache,
                ),
                call.apply_banking_data(
                    member=member,
                    iban="test_iban",
                    account_owner="test_account_owner",
                    sepa_allowed=True,
                    cache=cache,
                ),
            ],
            manager.mock_calls,
        )
