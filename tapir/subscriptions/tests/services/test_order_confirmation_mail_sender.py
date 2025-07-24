import datetime
from unittest.mock import patch, Mock

from tapir_mail.service.shortcuts import make_timezone_aware
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.subscriptions.services.order_confirmation_mail_sender import (
    OrderConfirmationMailSender,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    CoopShareTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestOrderConfirmationMailSender(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(TransactionalTrigger, "fire_action")
    def test_sendConfirmationMailIfNecessary_default_sendsMailToTheRelevantMembers(
        self, mock_fire_action: Mock
    ):
        # member 1 should get confirmation for both subscription and coop shares
        member_1 = MemberFactory.create()
        subscription_member_1 = SubscriptionFactory.create(
            member=member_1, admin_confirmed=None, quantity=2, product__name="Product 1"
        )
        purchase_member_1 = CoopShareTransactionFactory.create(
            admin_confirmed=None, quantity=5, member=member_1
        )
        # member 2 should get confirmation for just subscriptions
        member_2 = MemberFactory.create()
        subscription_member_2 = SubscriptionFactory.create(
            member=member_2, admin_confirmed=None, quantity=7, product__name="Product 2"
        )
        # member 3 doesn't get confirmed, they should not receive any mail
        member_3 = MemberFactory.create()
        SubscriptionFactory.create(member=member_3, admin_confirmed=None)
        # member 4 gets confirmed by the admin but the automatic confirmation happened already,
        # they should not receive any email
        member_4 = MemberFactory.create()
        subscription_member_4 = SubscriptionFactory.create(
            member=member_4, auto_confirmed=make_timezone_aware(datetime.datetime.now())
        )

        OrderConfirmationMailSender.send_confirmation_mail_if_necessary(
            confirm_creation_ids=[
                subscription_member_1.id,
                subscription_member_2.id,
                subscription_member_4.id,
            ],
            confirm_purchase_ids=[purchase_member_1.id],
        )

        self.assertEqual(2, mock_fire_action.call_count)
        for call in mock_fire_action.call_args_list:
            transactional_trigger_data: TransactionalTriggerData = call.args[0]
            self.assertEqual(
                transactional_trigger_data.key, Events.ORDER_CONFIRMED_BY_ADMIN
            )
            self.assertIn(
                transactional_trigger_data.recipient_id_in_base_queryset,
                [member_1.id, member_2.id],
            )
            if transactional_trigger_data.recipient_id_in_base_queryset == member_1.id:
                self.assertEqual(
                    5, transactional_trigger_data.token_data["number_of_coop_shares"]
                )
                self.assertIn(
                    "2 × Product 1",
                    transactional_trigger_data.token_data["contract_list"],
                )

            if transactional_trigger_data.recipient_id_in_base_queryset == member_2.id:
                self.assertEqual(
                    0, transactional_trigger_data.token_data["number_of_coop_shares"]
                )
                self.assertIn(
                    "7 × Product 2",
                    transactional_trigger_data.token_data["contract_list"],
                )
