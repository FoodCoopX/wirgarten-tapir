from datetime import datetime

from tapir.associations.models import AssociationMembershipType
from tapir.utils.services.tapir_cache import TapirCache


class AssociationMembershipTypePriceGetter:
    @classmethod
    def get_price(
        cls,
        membership_type: AssociationMembershipType,
        reference_date: datetime.date,
        cache: dict,
    ):
        price_object = TapirCache.get_association_membership_price_object_at_date(
            type_id=membership_type.id, cache=cache, reference_date=reference_date
        )
        if price_object:
            return price_object.price
        return 0
