import datetime
from decimal import Decimal

from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.models import Member


class JokerValueService:
    @classmethod
    def get_joker_credit_value_for_single_joker(
        cls, member: Member, joker_date: datetime.date, cache: dict
    ) -> Decimal:
        subscription_price = (
            DeliveryPriceCalculator.get_price_of_subscriptions_delivered_in_week(
                member=member,
                reference_date=joker_date,
                only_subscriptions_affected_by_jokers=True,
                cache=cache,
            )
        )
        if subscription_price <= 0:
            return Decimal(0)

        # The joker week is still billed the pickup-location delivery charge, so
        # it is part of what gets credited back to the member.
        pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=member.id, reference_date=joker_date, cache=cache
            )
        )
        if pickup_location_id is None:
            return subscription_price

        return (
            subscription_price
            + PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
                pickup_location_id=pickup_location_id,
                reference_date=joker_date,
                cache=cache,
            )
        )
