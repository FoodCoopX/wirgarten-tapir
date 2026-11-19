from dataclasses import dataclass

from tapir.wirgarten.models import Product

type TapirOrder = dict[Product, int]


@dataclass(frozen=True)
class ContractPrerequisitesInput:
    desired_pickup_location_id: str | None
    payment_rhythm: str | None
    iban: str
    account_owner: str
    sepa_mandate_confirmed: bool
