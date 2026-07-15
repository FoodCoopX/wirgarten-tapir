import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.utils import get_today


class PickupLocationDeliveryChargeService:
    FUTURE_ONLY_ERROR_MESSAGE = (
        "Ein Lieferzuschlag kann nur für die Zukunft angelegt oder geändert werden."
    )
    PAST_DELETE_ERROR_MESSAGE = "Nur zukünftige Lieferzuschläge können gelöscht werden."

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
        if valid_from <= get_today(cache=cache):
            raise ValidationError(cls.FUTURE_ONLY_ERROR_MESSAGE)

        charge, _ = PickupLocationDeliveryCharge.objects.update_or_create(
            pickup_location=pickup_location,
            valid_from=valid_from,
            defaults={"amount": amount},
        )
        return charge

    @classmethod
    def delete_charge(cls, charge_id: str, cache: dict) -> None:
        charge = PickupLocationDeliveryCharge.objects.get(id=charge_id)
        if charge.valid_from <= get_today(cache=cache):
            raise ValidationError(cls.PAST_DELETE_ERROR_MESSAGE)
        charge.delete()
