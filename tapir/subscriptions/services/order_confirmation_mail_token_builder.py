import datetime
from decimal import Decimal

from tapir_mail.models import StaticSegmentRecipient

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import Member, Subscription
from tapir.wirgarten.utils import format_currency, format_date, get_today


class OrderConfirmationMailTokenBuilder:
    NO_DELIVERY_TEXT = "Keine Lieferung"

    @classmethod
    def build_product_order_tokens(
        cls,
        member: Member,
        subscriptions: list[Subscription],
        solidarity_contribution: SolidarityContribution | None,
        cache: dict,
    ) -> dict:
        reference_date = min(subscription.start_date for subscription in subscriptions)
        return {
            "contract_list": cls.format_contract_list_with_prices(
                subscriptions=subscriptions,
                reference_date=reference_date,
                cache=cache,
            ),
            "first_pickup_date": cls.get_first_pickup_date_text(
                member=member,
                subscriptions=subscriptions,
                cache=cache,
            ),
            "monthly_total": cls.format_monthly_total(
                subscriptions=subscriptions,
                solidarity_contribution=solidarity_contribution,
                reference_date=reference_date,
                cache=cache,
            ),
            "payment_rhythm": cls.get_payment_rhythm_text(member=member, cache=cache),
        }

    @classmethod
    def build_membership_only_tokens(
        cls,
        member: Member,
        solidarity_contribution: SolidarityContribution | None,
        cache: dict,
    ) -> dict:
        return {
            "monthly_total": cls.format_monthly_total(
                subscriptions=[],
                solidarity_contribution=solidarity_contribution,
                reference_date=get_today(cache=cache),
                cache=cache,
            ),
            "payment_rhythm": cls.get_payment_rhythm_text(member=member, cache=cache),
        }

    @classmethod
    def format_contract_list_with_prices(
        cls,
        subscriptions: list[Subscription],
        reference_date: datetime.date,
        cache: dict,
    ) -> str:
        sorted_subscriptions = sorted(
            subscriptions, key=lambda subscription: subscription.product_id
        )
        formatted_subscriptions = [
            cls._format_subscription_with_price(
                subscription=subscription,
                reference_date=reference_date,
                cache=cache,
            )
            for subscription in sorted_subscriptions
        ]
        return f"<ul><li>{'</li><li>'.join(formatted_subscriptions)}</li></ul>"

    @classmethod
    def format_monthly_total(
        cls,
        subscriptions: list[Subscription],
        solidarity_contribution: SolidarityContribution | None,
        reference_date: datetime.date,
        cache: dict,
    ) -> str:
        total = Decimal(0)
        for subscription in subscriptions:
            total += cls._get_monthly_price_or_zero(
                subscription=subscription,
                reference_date=reference_date,
                cache=cache,
            )
        if solidarity_contribution is not None:
            total += Decimal(str(solidarity_contribution.amount))
        return format_currency(total)

    @classmethod
    def get_payment_rhythm_text(cls, member: Member, cache: dict) -> str:
        rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=get_today(cache=cache),
            cache=cache,
        )
        return MemberPaymentRhythmService.get_rhythm_display_name(rhythm)

    @classmethod
    def get_first_pickup_date_text(
        cls,
        member: Member,
        subscriptions: list[Subscription],
        cache: dict,
    ) -> str:
        first_pickup_date = datetime.date(year=datetime.MAXYEAR, month=12, day=31)
        at_least_one_product_with_delivery = False
        for subscription in subscriptions:
            if subscription.product.type.delivery_cycle == NO_DELIVERY[0]:
                continue
            at_least_one_product_with_delivery = True
            next_delivery_date = DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                reference_date=subscription.start_date,
                pickup_location_id=MemberPickupLocationGetter.get_member_pickup_location_id(
                    member, subscription.start_date
                ),
                product_type=subscription.product.type,
                check_for_weeks_without_delivery=True,
                cache=cache,
            )
            if next_delivery_date is not None:
                first_pickup_date = min(first_pickup_date, next_delivery_date)

        if not at_least_one_product_with_delivery:
            return cls.NO_DELIVERY_TEXT
        return format_date(first_pickup_date)

    @classmethod
    def get_first_pickup_date_for_recipient(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ) -> str:
        if not isinstance(recipient, Member):
            return cls.NO_DELIVERY_TEXT

        subscriptions = list(
            recipient.subscription_set.select_related("product__type").order_by(
                "start_date"
            )
        )
        if len(subscriptions) == 0:
            return cls.NO_DELIVERY_TEXT

        return cls.get_first_pickup_date_text(
            member=recipient, subscriptions=subscriptions, cache=cache
        )

    @classmethod
    def _format_subscription_with_price(
        cls,
        subscription: Subscription,
        reference_date: datetime.date,
        cache: dict,
    ) -> str:
        monthly_price = cls._get_monthly_price_or_none(
            subscription=subscription,
            reference_date=reference_date,
            cache=cache,
        )
        if monthly_price is None:
            return subscription.long_str()
        return f"{subscription.long_str()} — {format_currency(monthly_price)} € / Monat"

    @classmethod
    def _get_monthly_price_or_none(
        cls,
        subscription: Subscription,
        reference_date: datetime.date,
        cache: dict,
    ) -> Decimal | None:
        try:
            return SubscriptionPriceCalculator.get_monthly_price(
                subscription=subscription,
                reference_date=reference_date,
                cache=cache,
            )
        except TapirImproperlyConfigured:
            return None

    @classmethod
    def _get_monthly_price_or_zero(
        cls,
        subscription: Subscription,
        reference_date: datetime.date,
        cache: dict,
    ) -> Decimal:
        monthly_price = cls._get_monthly_price_or_none(
            subscription=subscription,
            reference_date=reference_date,
            cache=cache,
        )
        if monthly_price is None:
            return Decimal(0)
        return monthly_price
