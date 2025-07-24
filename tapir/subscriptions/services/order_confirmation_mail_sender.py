from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Subscription, CoopShareTransaction
from tapir.wirgarten.utils import format_subscription_list_html


class OrderConfirmationMailSender:
    @staticmethod
    def send_confirmation_mail_if_necessary(confirm_creation_ids, confirm_purchase_ids):
        if len(confirm_creation_ids) == 0 and len(confirm_purchase_ids) == 0:
            return

        data_by_member = {}

        for subscription in Subscription.objects.filter(
            id__in=confirm_creation_ids
        ).select_related("member"):
            if subscription.auto_confirmed is not None:
                continue
            if subscription.member not in data_by_member.keys():
                data_by_member[subscription.member] = {
                    "subscriptions": [],
                    "number_of_coop_shares": 0,
                }
            data_by_member[subscription.member]["subscriptions"].append(subscription)

        for share_transaction in CoopShareTransaction.objects.filter(
            id__in=confirm_purchase_ids
        ).select_related("member"):
            if share_transaction.auto_confirmed is not None:
                continue
            if share_transaction.member not in data_by_member.keys():
                data_by_member[share_transaction.member] = {
                    "subscriptions": [],
                    "number_of_coop_shares": 0,
                }

            data_by_member[share_transaction.member][
                "number_of_coop_shares"
            ] += share_transaction.quantity

        for member, data in data_by_member.items():
            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key=Events.ORDER_CONFIRMED_BY_ADMIN,
                    recipient_id_in_base_queryset=member.id,
                    token_data={
                        "contract_list": format_subscription_list_html(
                            data["subscriptions"]
                        ),
                        "number_of_coop_shares": data["number_of_coop_shares"],
                    },
                ),
            )
