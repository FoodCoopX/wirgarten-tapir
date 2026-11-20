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
class AdminSizeChange:
    member: Member
    subscription: Subscription
    new_product: Product
    change_date: datetime.date
    order: TapirOrder
    prerequisites: SubscriptionPrerequisitesInput


@dataclass(frozen=True)
class AdminSubscriptionAddition:
    member: Member
    product: Product
    quantity: int
    start_date: datetime.date
    prerequisites: SubscriptionPrerequisitesInput


@dataclass(frozen=True)
class DateOption:
    date: datetime.date | None
    enabled: bool


@dataclass(frozen=True)
class WeekOption:
    date: datetime.date
    is_before_next_possible_start: bool
    has_no_delivery: bool


@dataclass(frozen=True)
class StartDateOptions:
    next_possible_start: DateOption
    weeks: list[WeekOption]
    next_period_start: DateOption
