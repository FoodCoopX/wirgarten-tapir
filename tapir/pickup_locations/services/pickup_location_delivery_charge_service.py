import datetime
from decimal import Decimal

from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.utils.services.tapir_cache import TapirCache


class PickupLocationDeliveryChargeService:
    @classmethod
    def get_delivery_charge_at_date(
        cls,
        pickup_location_id: str,
        reference_date: datetime.date,
        cache: dict,
    ) -> Decimal:
        location_cache = get_from_cache_or_compute(
            cache, pickup_location_id, lambda: {}
        )
        charge_by_date_cache = get_from_cache_or_compute(
            location_cache, "delivery_charge_by_date", lambda: {}
        )

        def compute():
            charges = list(
                TapirCache.get_delivery_charges_by_pickup_location_id(
                    cache=cache, pickup_location_id=pickup_location_id
                )
            )
            charges = [
                charge for charge in charges if charge.valid_from <= reference_date
            ]
            if not charges:
                return Decimal("0.00")
            charges.sort(key=lambda charge: charge.valid_from, reverse=True)
            return charges[0].amount

        return get_from_cache_or_compute(charge_by_date_cache, reference_date, compute)
