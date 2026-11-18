from tapir.payments.models import MemberCredit
from tapir.wirgarten.models import (
    Deliveries,
    MemberPickupLocation,
    Payment,
    PickupLocation,
    WaitingListPickupLocationWish,
)


class PickupLocationDeletionValidator:
    IN_USE_MESSAGE = (
        "Der Abholort kann nicht gelöscht werden, er wird noch verwendet von: {usages}."
    )
    USAGES = [
        (MemberPickupLocation, "Mitgliedern"),
        (MemberCredit, "Gutschriften"),
        (Payment, "Zahlungen"),
        (Deliveries, "Lieferungen"),
        (WaitingListPickupLocationWish, "Wartelisten-Wünschen"),
    ]

    @classmethod
    def validate(cls, pickup_location: PickupLocation) -> str | None:
        usages = [
            label
            for model, label in cls.USAGES
            if model.objects.filter(pickup_location=pickup_location).exists()
        ]
        if not usages:
            return None
        return cls.IN_USE_MESSAGE.format(usages=", ".join(usages))
