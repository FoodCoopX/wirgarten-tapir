import datetime
from decimal import Decimal

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation


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

    @classmethod
    def save_charge(
        cls,
        pickup_location: PickupLocation,
        amount: Decimal,
        valid_from: datetime.date,
        cache: dict,
    ) -> PickupLocationDeliveryCharge:
        existing = PickupLocationDeliveryCharge.objects.filter(
            pickup_location=pickup_location, valid_from=valid_from
        ).first()
        if existing is not None:
            existing.amount = amount
            existing.save()
            return existing
        return PickupLocationDeliveryCharge.objects.create(
            pickup_location=pickup_location,
            amount=amount,
            valid_from=valid_from,
        )
