import datetime
from decimal import Decimal

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)


class BiddingRoundDeliveryChargeService:
    @classmethod
    def get_yearly_delivery_charge(
        cls, pickup_location_id, product_type, growing_period, cache
    ) -> Decimal:
        if not pickup_location_id or product_type is None or growing_period is None:
            return Decimal("0.00")

        total = Decimal("0.00")
        current_date = growing_period.start_date - datetime.timedelta(days=1)
        while current_date <= growing_period.end_date:
            next_date = DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                reference_date=current_date,
                pickup_location_id=pickup_location_id,
                product_type=product_type,
                check_for_weeks_without_delivery=True,
                cache=cache,
            )
            if next_date is None or next_date > growing_period.end_date:
                break
            total += PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
                pickup_location_id=pickup_location_id,
                reference_date=next_date,
                cache=cache,
            )
            current_date = next_date
        return total
