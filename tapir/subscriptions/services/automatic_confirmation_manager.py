import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.order_confirmation_mail_sender import (
    OrderConfirmationMailSender,
)
from tapir.wirgarten.models import Subscription, CoopShareTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.utils import get_today, get_now


class AutomaticConfirmationManager:
    @classmethod
    def confirm_subscriptions_and_coop_share_purchases_if_necessary(cls):
        cache = {}

        subscriptions = Subscription.objects.filter(
            admin_confirmed__isnull=True, auto_confirmed__isnull=True
        )
        subscriptions_ids_to_confirm = cls.get_objects_ids_to_confirm(
            objects=subscriptions, field_name="start_date", cache=cache
        )
        Subscription.objects.filter(id__in=subscriptions_ids_to_confirm).update(
            auto_confirmed=get_now(cache=cache)
        )

        transactions = CoopShareTransaction.objects.filter(
            admin_confirmed__isnull=True,
            auto_confirmed__isnull=True,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        )
        transactions_ids_to_confirm = cls.get_objects_ids_to_confirm(
            objects=transactions, field_name="valid_at", cache=cache
        )
        CoopShareTransaction.objects.filter(id__in=transactions_ids_to_confirm).update(
            auto_confirmed=get_now(cache=cache)
        )

        OrderConfirmationMailSender.send_confirmation_mail_if_necessary(
            confirm_creation_ids=subscriptions_ids_to_confirm,
            confirm_purchase_ids=transactions_ids_to_confirm,
        )

    @classmethod
    def get_objects_ids_to_confirm(cls, objects, field_name: str, cache: dict):
        objects_ids_to_confirm = []
        today = get_today(cache=cache)
        for obj in objects:
            object_valid_at = getattr(obj, field_name)
            if object_valid_at < today:
                objects_ids_to_confirm.append(obj.id)
                continue

            first_delivery_after_validity = get_next_delivery_date(
                reference_date=object_valid_at, cache=cache
            )
            weekday_limit = get_parameter_value(
                ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, cache=cache
            )
            date_after_which_the_object_must_be_confirmed = (
                first_delivery_after_validity
            )
            while (
                date_after_which_the_object_must_be_confirmed.weekday() != weekday_limit
            ):
                date_after_which_the_object_must_be_confirmed -= datetime.timedelta(
                    days=1
                )

            if date_after_which_the_object_must_be_confirmed < today:
                objects_ids_to_confirm.append(obj.id)

        return objects_ids_to_confirm
