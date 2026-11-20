import datetime
from dataclasses import dataclass

from tapir.wirgarten.models import Member, Product, Subscription

type TapirOrder = dict[Product, int]


@dataclass(frozen=True)
class SubscriptionPrerequisitesInput:
    desired_pickup_location_id: str | None
    iban: str
    account_owner: str
    sepa_mandate_confirmed: bool


@dataclass(frozen=True)
class AdminSizeChangeRequest:
    member: Member
    subscription: Subscription
    new_product: Product
    change_date: datetime.date
    order: TapirOrder
    prerequisites: SubscriptionPrerequisitesInput
