import datetime
from dataclasses import dataclass

from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, Subscription
from tapir.wirgarten.utils import get_today


@dataclass(frozen=True)
class MemberSummary:
    id: str
    display_name: str
    member_number: str | None


@dataclass(frozen=True)
class SubscriptionUnit:
    subscription_id: str
    unit_number: int
    product_type_id: str
    product_type_name: str
    product_id: str
    product_name: str
    start_date: datetime.date
    end_date: datetime.date
    status: str
    price_category: str


@dataclass(frozen=True)
class SubscriptionPrerequisitesStatus:
    pickup_location_name: str | None
    has_banking_data: bool


class AdminSubscriptionChangeMemberDataBuilder:
    STATUS_RUNNING = "running"
    STATUS_PLANNED = "planned"
    STATUS_CANCELLED = "cancelled"
    STATUS_ENDED = "ended"
    STATUSES = [STATUS_RUNNING, STATUS_PLANNED, STATUS_CANCELLED, STATUS_ENDED]

    PRICE_STANDARD = "standard"
    PRICE_PERSONALISED = "personalised"
    PRICE_EXEMPT = "exempt"
    PRICE_CATEGORIES = [PRICE_STANDARD, PRICE_PERSONALISED, PRICE_EXEMPT]

    @classmethod
    def build_member_summary(cls, member: Member, cache: dict) -> MemberSummary:
        return MemberSummary(
            id=member.id,
            display_name=f"{member.first_name} {member.last_name}",
            member_number=MemberNumberService.format_member_number(
                member_number=member.member_no, cache=cache
            ),
        )

    @classmethod
    def build_subscription_units(
        cls, member: Member, cache: dict
    ) -> list[SubscriptionUnit]:
        today = get_today(cache=cache)
        current_growing_period = TapirCache.get_growing_period_at_date(
            reference_date=today, cache=cache
        )
        oldest_relevant_end_date = (
            current_growing_period.start_date
            if current_growing_period is not None
            else today
        )

        subscriptions = sorted(
            (
                subscription
                for subscription in TapirCache.get_all_subscriptions_for_member(
                    member_id=member.id, cache=cache
                )
                if subscription.end_date >= oldest_relevant_end_date
            ),
            key=lambda subscription: (
                subscription.product.type.name,
                subscription.start_date,
                subscription.product.name,
            ),
        )

        return [
            SubscriptionUnit(
                subscription_id=subscription.id,
                unit_number=unit_number,
                product_type_id=subscription.product.type_id,
                product_type_name=subscription.product.type.name,
                product_id=subscription.product_id,
                product_name=subscription.product.name,
                start_date=subscription.start_date,
                end_date=subscription.end_date,
                status=cls.get_status(subscription=subscription, today=today),
                price_category=cls.get_price_category(subscription),
            )
            for subscription in subscriptions
            for unit_number in range(1, subscription.quantity + 1)
        ]

    @classmethod
    def get_status(cls, subscription: Subscription, today: datetime.date) -> str:
        if subscription.end_date < today:
            return cls.STATUS_ENDED
        if subscription.cancellation_ts is not None:
            return cls.STATUS_CANCELLED
        if subscription.start_date > today:
            return cls.STATUS_PLANNED
        return cls.STATUS_RUNNING

    @classmethod
    def get_price_category(cls, subscription: Subscription) -> str:
        if subscription.price_override is None:
            return cls.PRICE_STANDARD
        if subscription.price_override == 0:
            return cls.PRICE_EXEMPT
        return cls.PRICE_PERSONALISED

    @classmethod
    def build_prerequisites_status(
        cls, member: Member, cache: dict
    ) -> SubscriptionPrerequisitesStatus:
        today = get_today(cache=cache)
        pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
            member=member, reference_date=today, cache=cache
        )
        return SubscriptionPrerequisitesStatus(
            pickup_location_name=(
                pickup_location.name if pickup_location is not None else None
            ),
            has_banking_data=not MemberNeedsBankingDataChecker.does_member_need_banking_data(
                member
            ),
        )
