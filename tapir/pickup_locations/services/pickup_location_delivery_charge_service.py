import datetime
from decimal import Decimal

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
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
        charges = TapirCache.get_delivery_charges_by_pickup_location_id(
            cache=cache, pickup_location_id=pickup_location_id
        )
        applicable = [
            charge for charge in charges if charge.valid_from <= reference_date
        ]
        if not applicable:
            return Decimal("0.00")
        return max(applicable, key=lambda charge: charge.valid_from).amount

    @classmethod
    def save_charge(
        cls,
        pickup_location: PickupLocation,
        amount: Decimal,
        valid_from: datetime.date,
        cache: dict,
    ) -> PickupLocationDeliveryCharge:
        charge, _ = PickupLocationDeliveryCharge.objects.update_or_create(
            pickup_location=pickup_location,
            valid_from=valid_from,
            defaults={"amount": amount},
        )
        return charge
