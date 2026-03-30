from tapir_mail.models import StaticSegmentRecipient

from tapir.wirgarten.models import Member
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.products import get_active_subscriptions
from tapir.wirgarten.utils import (
    format_subscription_list_html,
    format_currency,
)


class SubscriptionMailTokenService:
    @classmethod
    def contract_list_on_next_delivery(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        if not isinstance(recipient, Member):
            return None

        next_delivery_date = get_next_delivery_date(cache=cache)
        subscriptions = get_active_subscriptions(
            reference_date=next_delivery_date, cache=cache
        ).filter(member=recipient)

        return format_subscription_list_html(subs=subscriptions)

    @classmethod
    def total_price_on_next_delivery(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        if not isinstance(recipient, Member):
            return None

        next_delivery_date = get_next_delivery_date(cache=cache)
        subscriptions = get_active_subscriptions(
            reference_date=next_delivery_date, cache=cache
        ).filter(member=recipient)

        result = 0
        for subscription in subscriptions:
            result += float(
                subscription.total_price(reference_date=next_delivery_date, cache=cache)
            )

        return format_currency(result)

    @classmethod
    def solidarity_part_on_next_delivery(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        if not isinstance(recipient, Member):
            return None

        next_delivery_date = get_next_delivery_date(cache=cache)
        subscriptions = get_active_subscriptions(
            reference_date=next_delivery_date, cache=cache
        ).filter(member=recipient)

        result = 0
        for subscription in subscriptions:
            soli_part = float(
                subscription.total_price(reference_date=next_delivery_date, cache=cache)
            ) - float(
                subscription.total_price_without_soli(
                    reference_date=next_delivery_date, cache=cache
                )
            )
            result += soli_part

        return format_currency(result)
