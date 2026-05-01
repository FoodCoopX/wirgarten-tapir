import datetime
from decimal import Decimal
from typing import Set

from tapir.deliveries.models import (
    Joker,
    DeliveryDayAdjustment,
    DeliveryDonation,
    CustomCycleScheduledDeliveryWeek,
)
from tapir.payments.models import MemberPaymentRhythm
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.models import NoticePeriod
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import (
    Subscription,
    ProductType,
    Product,
    ProductPrice,
    PickupLocation,
    PickupLocationOpeningTime,
    CoopShareTransaction,
    ProductCapacity,
    GrowingPeriod,
    Member,
    TaxRate,
    MandateReference,
    Payment,
)
from tapir.wirgarten.service.product_standard_order import product_type_order_by
from tapir.wirgarten.utils import get_today


class TapirCache:
    @classmethod
    def get_all_subscriptions(cls, cache: dict) -> Set[Subscription]:
        key = "all_subscriptions"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )
        return get_from_cache_or_compute(
            cache,
            key,
            lambda: set(
                Subscription.objects.select_related(
                    "member", "product", "product__type", "mandate_ref"
                )
            ),
        )

    @classmethod
    def get_all_solidarity_contributions(
        cls, cache: dict
    ) -> Set[SolidarityContribution]:
        return get_from_cache_or_compute(
            cache,
            "all_solidarity_contributions",
            lambda: set(SolidarityContribution.objects.select_related("member")),
        )

    @classmethod
    def get_subscriptions_active_at_date(
        cls, reference_date: datetime.date, cache: dict
    ):
        key = "subscriptions_by_date"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        def compute():
            all_subscriptions = cls.get_all_subscriptions(cache)
            return {
                subscription
                for subscription in all_subscriptions
                if subscription.start_date <= reference_date
                and (
                    subscription.end_date is None
                    or reference_date <= subscription.end_date
                )
            }

        subscriptions_by_date = get_from_cache_or_compute(cache, key, lambda: {})
        return get_from_cache_or_compute(subscriptions_by_date, reference_date, compute)

    @classmethod
    def get_solidarity_contributions_active_at_date(
        cls, reference_date: datetime.date, cache: dict
    ) -> set[SolidarityContribution]:
        def compute():
            all_contributions = cls.get_all_solidarity_contributions(cache)
            return {
                contribution
                for contribution in all_contributions
                if contribution.start_date <= reference_date <= contribution.end_date
            }

        contributions_by_date = get_from_cache_or_compute(
            cache, "solidarity_contributions_by_date", lambda: {}
        )
        return get_from_cache_or_compute(contributions_by_date, reference_date, compute)

    @classmethod
    def get_active_and_future_subscriptions_by_member_id(
        cls, cache: dict, reference_date: datetime.date
    ):
        key = "subscriptions_by_date_and_member_id"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        def compute():
            from tapir.wirgarten.service.products import (
                get_active_and_future_subscriptions,
            )

            subscriptions_by_member_id = {}
            for subscription in get_active_and_future_subscriptions(
                reference_date=reference_date, cache=cache
            ):
                if subscription.member_id not in subscriptions_by_member_id:
                    subscriptions_by_member_id[subscription.member_id] = []
                subscriptions_by_member_id[subscription.member_id].append(subscription)
            return subscriptions_by_member_id

        subscriptions_by_date_and_member_id = get_from_cache_or_compute(
            cache, key, lambda: {}
        )
        return get_from_cache_or_compute(
            subscriptions_by_date_and_member_id, reference_date, compute
        )

    @classmethod
    def get_subscriptions_by_delivery_cycle(
        cls, cache: dict, delivery_cycle
    ) -> Set[Subscription]:
        key = "subscriptions_by_delivery_cycle"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        subscriptions_by_delivery_cycle = get_from_cache_or_compute(
            cache, key, lambda: {}
        )
        return get_from_cache_or_compute(
            subscriptions_by_delivery_cycle,
            delivery_cycle,
            lambda: set(
                Subscription.objects.filter(
                    product__type__delivery_cycle=delivery_cycle
                ).order_by("id")
            ),
        )

    @classmethod
    def get_subscriptions_affected_by_jokers(cls, cache: dict):
        key = "subscriptions_affected_by_jokers"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        return get_from_cache_or_compute(
            cache,
            key,
            lambda: Subscription.objects.filter(
                product__type__is_affected_by_jokers=True
            ),
        )

    @classmethod
    def get_product_type_by_id(cls, cache: dict, product_type_id: str):
        product_types_by_id = get_from_cache_or_compute(
            cache, "product_types_by_id", lambda: {}
        )
        return get_from_cache_or_compute(
            product_types_by_id,
            product_type_id,
            lambda: ProductType.objects.get(id=product_type_id),
        )

    @classmethod
    def get_products_with_product_type(cls, cache: dict, product_type_id: str):
        product_by_product_type_id = get_from_cache_or_compute(
            cache, "product_by_product_type_id", lambda: {}
        )

        return get_from_cache_or_compute(
            product_by_product_type_id,
            product_type_id,
            lambda: set(Product.objects.filter(type_id=product_type_id)),
        )

    @classmethod
    def get_product_prices_by_product_id(cls, cache: dict, product_id: str):
        product_prices_by_product_id = get_from_cache_or_compute(
            cache, "product_prices_by_product_id", lambda: {}
        )

        def compute():
            return set(
                ProductPrice.objects.filter(product_id=product_id).order_by(
                    "valid_from"
                )
            )

        return get_from_cache_or_compute(
            product_prices_by_product_id,
            product_id,
            compute,
        )

    @classmethod
    def get_all_products(cls, cache: dict):
        return get_from_cache_or_compute(
            cache, "all_products", lambda: set(Product.objects.order_by("id"))
        )

    @classmethod
    def get_all_product_types(cls, cache: dict):
        return get_from_cache_or_compute(
            cache, "all_product_types", lambda: set(ProductType.objects.order_by("id"))
        )

    @classmethod
    def get_subscriptions_by_product_type(cls, cache: dict):
        key = "subscriptions_by_product_type"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        def compute():
            subscriptions_by_product_type = {
                product_type: set()
                for product_type in ProductType.objects.order_by(
                    *product_type_order_by(cache=cache)
                )
            }
            subscriptions = Subscription.objects.select_related("product__type")
            for subscription in subscriptions:
                subscriptions_by_product_type[subscription.product.type].add(
                    subscription
                )
            return subscriptions_by_product_type

        return get_from_cache_or_compute(cache, key, compute)

    @classmethod
    def get_product_by_name_iexact(cls, cache: dict, product_name: str):
        products = cls.get_all_products(cache)

        products_by_name_iexact = get_from_cache_or_compute(
            cache, "products_by_name_iexact", lambda: {}
        )

        def name_matches(product: Product):
            return product.name.casefold() == product_name.casefold()

        return get_from_cache_or_compute(
            products_by_name_iexact,
            product_name,
            lambda: next(filter(name_matches, products), None),
        )

    @classmethod
    def get_last_subscription(cls, cache: dict):
        key = "last_subscription"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        return get_from_cache_or_compute(
            cache,
            key,
            lambda: Subscription.objects.filter(end_date__isnull=False)
            .order_by("end_date")
            .last(),
        )

    @classmethod
    def get_product_types_in_standard_order(cls, cache: dict):
        return get_from_cache_or_compute(
            cache,
            "product_types_in_standard_order",
            lambda: ProductType.objects.order_by(*product_type_order_by(cache=cache)),
        )

    @classmethod
    def get_pickup_location_by_id(cls, cache: dict, pickup_location_id):
        if pickup_location_id is None:
            return None

        def compute():
            return {
                pickup_location.id: pickup_location
                for pickup_location in PickupLocation.objects.all()
            }

        pickup_location_by_id_cache = get_from_cache_or_compute(
            cache, "pickup_location_by_id", lambda: compute()
        )
        return pickup_location_by_id_cache.get(pickup_location_id, None)

    @classmethod
    def get_product_by_id(cls, cache: dict, product_id):
        if product_id is None:
            return None

        def compute():
            return {
                product.id: product
                for product in Product.objects.select_related("type")
            }

        product_by_id_cache = get_from_cache_or_compute(
            cache, "product_by_id", lambda: compute()
        )
        return product_by_id_cache.get(product_id, None)

    @classmethod
    def get_opening_times_by_pickup_location_id(cls, cache: dict, pickup_location_id):
        opening_times_by_pickup_location_id_cache = get_from_cache_or_compute(
            cache, "opening_times_by_pickup_location_id", lambda: {}
        )
        return get_from_cache_or_compute(
            opening_times_by_pickup_location_id_cache,
            pickup_location_id,
            lambda: list(
                PickupLocationOpeningTime.objects.filter(
                    pickup_location_id=pickup_location_id
                )
            ),
        )

    @classmethod
    def get_unconfirmed_coop_share_purchases_by_member_id(cls, cache: dict):
        def compute():
            transactions = cls.get_unconfirmed_coop_share_purchases(cache=cache)
            transactions_by_member_id = {}
            for transaction in transactions:
                if transaction.member_id not in transactions_by_member_id:
                    transactions_by_member_id[transaction.member_id] = []
                transactions_by_member_id[transaction.member_id].append(transaction)
            return transactions_by_member_id

        return get_from_cache_or_compute(
            cache, "unconfirmed_coop_share_transactions_by_member_id", compute
        )

    @classmethod
    def get_unconfirmed_coop_share_purchases(cls, cache: dict):
        return get_from_cache_or_compute(
            cache,
            "unconfirmed_coop_share_purchases",
            lambda: list(
                CoopShareTransaction.objects.filter(
                    admin_confirmed__isnull=True,
                    transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                )
            ),
        )

    @classmethod
    def get_product_type_capacity_at_date(
        cls, cache: dict, product_type: ProductType, reference_date: datetime.date
    ):
        product_type_capacities_by_growing_period = get_from_cache_or_compute(
            cache, "product_type_capacities_by_growing_period", lambda: {}
        )
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=reference_date, cache=cache
        )
        product_type_capacities_by_product_type = get_from_cache_or_compute(
            product_type_capacities_by_growing_period, growing_period, lambda: {}
        )

        def compute():
            return ProductCapacity.objects.filter(
                product_type=product_type, period=growing_period
            ).first()

        return get_from_cache_or_compute(
            product_type_capacities_by_product_type,
            product_type,
            compute,
        )

    @classmethod
    def get_all_growing_periods_ascending(cls, cache: dict):
        return get_from_cache_or_compute(
            cache,
            "all_growing_periods",
            lambda: list(GrowingPeriod.objects.order_by("start_date")),
        )

    @classmethod
    def get_growing_period_at_date(
        cls, reference_date: datetime.date, cache: dict
    ) -> GrowingPeriod | None:
        if reference_date is None:
            reference_date = get_today(cache=cache)

        def compute():
            growing_periods = cls.get_all_growing_periods_ascending(cache=cache)
            for growing_period in growing_periods:
                if (
                    growing_period.start_date
                    <= reference_date
                    <= growing_period.end_date
                ):
                    return growing_period
            return None

        growing_periods_by_date_cache = get_from_cache_or_compute(
            cache, "growing_periods_by_date", lambda: {}
        )
        return get_from_cache_or_compute(
            growing_periods_by_date_cache, reference_date, compute
        )

    @classmethod
    def get_payment_rhythms_objects_by_member(
        cls, cache: dict
    ) -> dict[Member, list[MemberPaymentRhythm]]:
        def compute():
            result = {}
            all_rhythms = MemberPaymentRhythm.objects.select_related("member").order_by(
                "valid_from"
            )
            for rhythm in all_rhythms:
                if rhythm.member not in result:
                    result[rhythm.member] = []
                result[rhythm.member].append(rhythm)
            return result

        return get_from_cache_or_compute(cache, "payment_rhythms_by_member", compute)

    @classmethod
    def get_member_payment_rhythm_object(
        cls, member: Member, reference_date: datetime.date, cache: dict
    ):
        payment_rhythms_by_member = cls.get_payment_rhythms_objects_by_member(
            cache=cache
        )
        member_payment_rhythms = payment_rhythms_by_member.get(member, [])

        rhythm_at_date = None
        for rhythm in member_payment_rhythms:
            # member_payment_rhythms is assumed sorted by valid_from ascending
            if rhythm.valid_from <= reference_date:
                rhythm_at_date = rhythm

        return rhythm_at_date

    @classmethod
    def get_payments_by_mandate_ref_and_type(
        cls, cache: dict, payment_type: str, mandate_ref: MandateReference
    ) -> set[Payment]:
        def compute():
            payments = Payment.objects.select_related("mandate_ref")
            result = {}
            for payment in payments:
                if payment.mandate_ref not in result:
                    result[payment.mandate_ref] = {}
                if payment.type not in result[payment.mandate_ref]:
                    result[payment.mandate_ref][payment.type] = set()
                result[payment.mandate_ref][payment.type].add(payment)
            return result

        payments_by_mandate_ref_and_product_type = get_from_cache_or_compute(
            cache=cache,
            key="payments_by_mandate_ref_and_type",
            compute_function=compute,
        )

        return payments_by_mandate_ref_and_product_type.get(mandate_ref, {}).get(
            payment_type, set()
        )

    @classmethod
    def get_product_type_tax_rates(cls, product_type: ProductType, cache: dict):
        tax_rates_by_product_type = get_from_cache_or_compute(
            cache=cache, key="tax_rates_by_product_type", compute_function=lambda: {}
        )

        def compute():
            return TaxRate.objects.filter(product_type=product_type)

        return get_from_cache_or_compute(
            cache=tax_rates_by_product_type, key=product_type, compute_function=compute
        )

    @classmethod
    def get_notice_period_object(
        cls,
        product_type: ProductType,
        growing_period: GrowingPeriod,
        cache: dict,
    ):
        notice_period_by_product_type = get_from_cache_or_compute(
            cache=cache,
            key="notice_period_by_product_type",
            compute_function=lambda: {},
        )
        notice_period_by_growing_period = get_from_cache_or_compute(
            cache=notice_period_by_product_type,
            key=product_type,
            compute_function=lambda: {},
        )

        return get_from_cache_or_compute(
            cache=notice_period_by_growing_period,
            key=growing_period,
            compute_function=lambda: NoticePeriod.objects.filter(
                product_type=product_type,
                growing_period=growing_period,
            ).first(),
        )

    @classmethod
    def get_member_solidarity_contribution_at_date(
        cls, member_id: str, reference_date: datetime.date, cache: dict
    ) -> Decimal:
        solidarity_contributions_by_member_id = get_from_cache_or_compute(
            cache=cache,
            key="solidarity_contributions_by_member_id",
            compute_function=lambda: {},
        )

        contributions_for_this_member = get_from_cache_or_compute(
            cache=solidarity_contributions_by_member_id,
            key=member_id,
            compute_function=lambda: {},
        )

        def compute() -> Decimal:
            return sum(
                SolidarityContribution.objects.filter(
                    member_id=member_id,
                    start_date__lte=reference_date,
                    end_date__gte=reference_date,
                ).values_list("amount", flat=True),
                start=Decimal(0),
            )

        return get_from_cache_or_compute(
            cache=contributions_for_this_member,
            key=reference_date,
            compute_function=compute,
        )

    @classmethod
    def get_base_product_by_product_type_id(cls, product_type_id: str, cache: dict):
        base_product_by_product_type_id = get_from_cache_or_compute(
            cache=cache,
            key="base_product_by_product_type_id",
            compute_function=lambda: {},
        )

        return get_from_cache_or_compute(
            base_product_by_product_type_id,
            key=product_type_id,
            compute_function=lambda: Product.objects.filter(
                type_id=product_type_id, base=True
            ).first(),
        )

    @classmethod
    def get_number_of_jokers_used_by_member_in_growing_period(
        cls, member_id: str, growing_period: GrowingPeriod, cache: dict
    ):
        uses_by_member_id = get_from_cache_or_compute(
            cache=cache,
            key="number_of_jokers_used_by_member_in_growing_period",
            compute_function=lambda: {},
        )
        uses_by_growing_period_id = get_from_cache_or_compute(
            cache=uses_by_member_id, key=member_id, compute_function=lambda: {}
        )

        def compute():
            return Joker.objects.filter(
                member_id=member_id,
                date__gte=growing_period.start_date,
                date__lte=growing_period.end_date,
            ).count()

        return get_from_cache_or_compute(
            cache=uses_by_growing_period_id,
            key=growing_period.id,
            compute_function=compute,
        )

    @classmethod
    def get_all_jokers_for_member(cls, member_id: str, cache: dict):
        jokers_by_member_id = get_from_cache_or_compute(
            cache=cache, key="jokers_by_member_id", compute_function=lambda: {}
        )

        def compute():
            return list(Joker.objects.filter(member_id=member_id).order_by("date"))

        return get_from_cache_or_compute(
            cache=jokers_by_member_id, key=member_id, compute_function=compute
        )

    @classmethod
    def get_delivery_day_adjustment(
        cls, growing_period_id: str, calendar_week: int, cache: dict
    ):
        delivery_adjustment_by_growing_period_id = get_from_cache_or_compute(
            cache, "delivery_adjustments_by_growing_period_id", lambda: {}
        )

        def compute():
            adjustments = DeliveryDayAdjustment.objects.filter(
                growing_period_id=growing_period_id
            )
            return {adjustment.calendar_week: adjustment for adjustment in adjustments}

        delivery_adjustments_by_calendar_week = get_from_cache_or_compute(
            cache=delivery_adjustment_by_growing_period_id,
            key=growing_period_id,
            compute_function=compute,
        )

        return delivery_adjustments_by_calendar_week.get(calendar_week, None)

    @classmethod
    def get_all_delivery_donations_for_member(cls, member_id: str, cache: dict):
        donations_by_member_id = get_from_cache_or_compute(
            cache=cache, key="donations_by_member_id", compute_function=lambda: {}
        )

        def compute():
            return list(
                DeliveryDonation.objects.filter(member_id=member_id).order_by("date")
            )

        return get_from_cache_or_compute(
            cache=donations_by_member_id, key=member_id, compute_function=compute
        )

    @classmethod
    def get_delivered_weeks_for_custom_cycle(
        cls, product_type: ProductType, growing_period: GrowingPeriod, cache: dict
    ):
        delivery_weeks_by_product_type_and_growing_period = get_from_cache_or_compute(
            cache=cache,
            key="delivery_weeks_by_product_type_and_growing_period",
            compute_function=lambda: {},
        )
        delivery_weeks_by_growing_period = get_from_cache_or_compute(
            cache=delivery_weeks_by_product_type_and_growing_period,
            key=product_type,
            compute_function=lambda: {},
        )

        def compute():
            return set(
                CustomCycleScheduledDeliveryWeek.objects.filter(
                    product_type=product_type, growing_period=growing_period
                ).values_list("calendar_week", flat=True)
            )

        return get_from_cache_or_compute(
            cache=delivery_weeks_by_growing_period,
            key=growing_period,
            compute_function=compute,
        )

    @classmethod
    def get_all_scheduled_weeks_for_custom_cycle(
        cls, product_type: ProductType, cache: dict
    ):
        scheduled_weeks_by_product_type = get_from_cache_or_compute(
            cache=cache,
            key="scheduled_weeks_by_product_type",
            compute_function=lambda: {},
        )

        return get_from_cache_or_compute(
            cache=scheduled_weeks_by_product_type,
            key=product_type,
            compute_function=lambda: CustomCycleScheduledDeliveryWeek.objects.filter(
                product_type=product_type
            ),
        )
