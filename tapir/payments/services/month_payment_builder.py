import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ImproperlyConfigured
from pygments.lexers import q

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month, get_first_of_next_month
from tapir.wirgarten.constants import (
    NO_DELIVERY,
    WEEKLY,
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
)
from tapir.wirgarten.models import (
    Subscription,
    Payment,
    Member,
    ProductType,
    MandateReference,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref


class MonthPaymentBuilder:
    @classmethod
    def build_payments_for_month(
        cls,
        reference_date: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
    ) -> list[Payment]:
        first_of_month = reference_date.replace(day=1)

        payments_to_create_trial = cls.build_payments_for_subscriptions_in_trial(
            current_month=first_of_month,
            cache=cache,
            generated_payments=generated_payments,
        )

        payments_to_create_no_trial = cls.build_payments_for_subscriptions_not_in_trial(
            current_month=first_of_month,
            cache=cache,
            generated_payments=generated_payments.union(payments_to_create_trial),
        )

        return cls.combine_similar_payments(
            payments_to_create_no_trial + payments_to_create_trial
        )

    @staticmethod
    def filter_payments(payments):
        return [p for p in payments if p.mandate_ref.member_id == "R0N9SF0xMb"]

    @classmethod
    def build_payments_for_subscriptions_not_in_trial(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
    ) -> list[Payment]:
        subscriptions_not_in_trial = cls.get_current_and_renewed_subscriptions(
            cache=cache, first_of_month=current_month, is_in_trial=False
        )

        subscriptions_by_member_and_product_type = (
            cls.group_subscriptions_by_member_and_product_type(
                subscriptions_not_in_trial
            )
        )

        payments_to_create = []

        for (
            member,
            subscriptions_by_product_type,
        ) in subscriptions_by_member_and_product_type.items():
            rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=current_month, cache=cache
            )
            for product_type, subscriptions in subscriptions_by_product_type.items():
                payment = (
                    cls.build_payment_for_subscriptions_for_member_and_product_type(
                        member=member,
                        first_of_month=current_month,
                        subscriptions=subscriptions,
                        product_type=product_type,
                        rhythm=rhythm,
                        cache=cache,
                        generated_payments=generated_payments,
                        in_trial=False,
                    )
                )
                if payment is not None:
                    payments_to_create.append(payment)

        return payments_to_create

    @classmethod
    def build_payment_for_subscriptions_for_member_and_product_type(
        cls,
        member: Member,
        first_of_month: datetime.date,
        subscriptions,
        product_type: ProductType,
        rhythm: MemberPaymentRhythm,
        cache: dict,
        generated_payments: set[Payment],
        in_trial: bool,
    ) -> Payment | None:
        first_day_of_rhythm_period = (
            MemberPaymentRhythmService.get_first_day_of_rhythm_period(
                rhythm=rhythm, reference_date=first_of_month, cache=cache
            )
        )
        last_day_of_rhythm_period = (
            MemberPaymentRhythmService.get_last_day_of_rhythm_period(
                rhythm=rhythm, reference_date=first_of_month, cache=cache
            )
        )

        payment_start_date = get_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE, cache=cache
        )
        first_day_of_rhythm_period = max(payment_start_date, first_day_of_rhythm_period)
        if first_day_of_rhythm_period > last_day_of_rhythm_period:
            return None

        mandate_ref = get_or_create_mandate_ref(member=member, cache=cache)

        already_paid = cls.get_already_paid_amount(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            product_type_name=product_type.name,
            cache=cache,
            generated_payments=generated_payments,
        )
        total_to_pay = cls.get_total_to_pay(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            subscriptions=subscriptions,
            cache=cache,
        )

        new_payment_amount = total_to_pay - float(already_paid)
        new_payment_amount = Decimal(new_payment_amount).quantize(Decimal("0.01"))
        if new_payment_amount <= 0:
            return None

        payments_due_date = cls.get_payment_due_date_on_month(
            reference_date=(
                get_first_of_next_month(first_of_month) if in_trial else first_of_month
            ),
            cache=cache,
        )

        subscription_payment_range_start = cls.get_payment_range_start(
            cache=cache,
            first_day_of_rhythm_period=first_day_of_rhythm_period,
            generated_payments=generated_payments,
            last_day_of_rhythm_period=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            product_type=product_type,
        )

        return Payment(
            due_date=payments_due_date,
            amount=new_payment_amount,
            mandate_ref=mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=product_type.name,
            subscription_payment_range_start=subscription_payment_range_start,
            subscription_payment_range_end=last_day_of_rhythm_period,
        )

    @classmethod
    def get_payment_range_start(
        cls,
        first_day_of_rhythm_period: datetime.date,
        last_day_of_rhythm_period: datetime.date,
        mandate_ref: MandateReference,
        product_type: ProductType,
        generated_payments: set[Payment],
        cache: dict,
    ):
        relevant_past_payments = cls.get_relevant_past_payments(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            product_type_name=product_type.name,
            generated_payments=generated_payments,
            cache=cache,
        )
        if len(relevant_past_payments) == 0:
            return first_day_of_rhythm_period

        return max(
            [
                payment.subscription_payment_range_end
                for payment in relevant_past_payments
            ]
        ) + datetime.timedelta(days=1)

    @classmethod
    def get_total_to_pay(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        subscriptions: list[Subscription],
        cache: dict,
    ):
        subscriptions_active_within_period = [
            subscription
            for subscription in subscriptions
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=range_start,
                range_1_end=range_end,
                range_2_start=subscription.start_date,
                range_2_end=subscription.end_date,
            )
        ]
        total_to_pay = sum(
            [
                cls.get_amount_to_pay_for_subscription_within_range(
                    subscription=subscription,
                    range_start=range_start,
                    range_end=range_end,
                    cache=cache,
                )
                for subscription in subscriptions_active_within_period
            ]
        )
        return total_to_pay

    @classmethod
    def get_already_paid_amount(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        mandate_ref: MandateReference,
        product_type_name: str,
        cache: dict,
        generated_payments: set[Payment],
    ) -> Decimal:
        relevant_payments = cls.get_relevant_past_payments(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name=product_type_name,
            cache=cache,
            generated_payments=generated_payments,
        )

        return sum([payment.amount for payment in relevant_payments])

    @classmethod
    def get_relevant_past_payments(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        mandate_ref: MandateReference,
        product_type_name: str,
        cache: dict,
        generated_payments: set[Payment],
    ):
        existing_payments = TapirCache.get_payments_by_mandate_ref_and_product_type(
            cache=cache, mandate_ref=mandate_ref, product_type_name=product_type_name
        )

        existing_payments = existing_payments.union(
            [
                payment
                for payment in generated_payments
                if payment.mandate_ref == mandate_ref
                and payment.type == product_type_name
            ]
        )

        payments_for_this_period = [
            payment
            for payment in existing_payments
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=range_start,
                range_1_end=range_end,
                range_2_start=payment.subscription_payment_range_start,
                range_2_end=payment.subscription_payment_range_end,
            )
        ]

        return payments_for_this_period

    @classmethod
    def get_amount_to_pay_for_subscription_within_range(
        cls,
        subscription: Subscription,
        range_start: datetime.date,
        range_end: datetime.date,
        cache: dict,
    ):
        number_of_full_month_to_pay, number_of_single_deliveries_to_pay = (
            cls.get_number_of_months_and_deliveries_to_pay(
                range_start=range_start,
                range_end=range_end,
                subscription=subscription,
                cache=cache,
            )
        )

        full_months_price = (
            subscription.total_price(reference_date=range_start, cache=cache)
            * number_of_full_month_to_pay
        )
        single_deliveries_price = (
            number_of_single_deliveries_to_pay
            * DeliveryPriceCalculator.get_price_of_single_delivery_without_solidarity(
                subscription=subscription, at_date=range_start, cache=cache
            )
        )
        return full_months_price + float(single_deliveries_price)

    @classmethod
    def get_number_of_months_and_deliveries_to_pay(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        subscription: Subscription,
        cache: dict,
    ):
        current_month = range_start
        number_of_full_month_to_pay = 0
        number_of_single_deliveries_to_pay = 0
        while current_month < range_end:
            if not DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=range_start,
                range_1_end=range_end,
                range_2_start=subscription.start_date,
                range_2_end=subscription.end_date,
            ):
                continue
            if cls.is_month_fully_covered_by_subscription(
                subscription=subscription, first_of_month=current_month
            ):
                number_of_full_month_to_pay += 1
            else:
                number_of_deliveries = cls.get_number_of_deliveries_in_month(
                    subscription=subscription, first_of_month=current_month, cache=cache
                )
                if cls.should_pay_full_month_price(
                    number_of_deliveries=number_of_deliveries,
                    delivery_cycle=subscription.product.type.delivery_cycle,
                ):
                    number_of_full_month_to_pay += 1
                else:
                    number_of_single_deliveries_to_pay += number_of_deliveries

            current_month += relativedelta(months=1)
        return number_of_full_month_to_pay, number_of_single_deliveries_to_pay

    @classmethod
    def is_month_fully_covered_by_subscription(
        cls,
        subscription: Subscription,
        first_of_month: datetime.date,
    ):
        if not DateRangeOverlapChecker.do_ranges_overlap(
            range_1_start=first_of_month,
            range_1_end=get_last_day_of_month(first_of_month),
            range_2_start=subscription.start_date,
            range_2_end=subscription.end_date,
        ):
            return False

        if (
            first_of_month == subscription.start_date.replace(day=1)
            and subscription.start_date.day != 1
        ):
            return False
        if (
            first_of_month == subscription.end_date.replace(day=1)
            and subscription.end_date.day
            != get_last_day_of_month(subscription.end_date).day
        ):
            return False
        return True

    @classmethod
    def should_pay_full_month_price(
        cls, number_of_deliveries: int, delivery_cycle: str
    ):
        return (
            number_of_deliveries
            >= cls.get_number_of_deliveries_for_full_month_price(delivery_cycle)
        )

    @classmethod
    def get_number_of_deliveries_in_month(
        cls,
        subscription: Subscription,
        first_of_month: datetime.date,
        cache: dict,
    ):
        last_of_month = get_last_day_of_month(first_of_month)
        number_of_deliveries = 0

        # we start one day back so that deliveries on the first day of the month are counted
        current_date = first_of_month - datetime.timedelta(days=1)

        while current_date <= last_of_month:
            current_date = DeliveryDateCalculator.get_next_delivery_date_for_delivery_cycle(
                reference_date=current_date,
                pickup_location_id=MemberPickupLocationService.get_member_pickup_location_id_from_cache(
                    member_id=subscription.member_id,
                    reference_date=current_date,
                    cache=cache,
                ),
                delivery_cycle=subscription.product.type.delivery_cycle,
                cache=cache,
            )
            if (
                current_date <= last_of_month
                and subscription.start_date <= current_date <= subscription.end_date
            ):
                number_of_deliveries += 1

        return number_of_deliveries

    @classmethod
    def get_payment_due_date_on_month(cls, reference_date: datetime.date, cache: dict):
        return reference_date.replace(
            day=get_parameter_value(ParameterKeys.PAYMENT_DUE_DAY, cache=cache)
        )

    @classmethod
    def group_subscriptions_by_member_and_product_type(
        cls, subscriptions: list[Subscription]
    ) -> dict[Member, dict[ProductType, set[Subscription]]]:
        subscriptions_by_member_and_product_type: dict[
            Member, dict[ProductType, set[Subscription]]
        ] = {}
        for subscription in subscriptions:
            if (
                subscription.member
                not in subscriptions_by_member_and_product_type.keys()
            ):
                subscriptions_by_member_and_product_type[subscription.member] = {}

            subscriptions_by_product_type = subscriptions_by_member_and_product_type[
                subscription.member
            ]
            if subscription.product.type not in subscriptions_by_product_type.keys():
                subscriptions_by_product_type[subscription.product.type] = set()

            subscriptions_by_product_type[subscription.product.type].add(subscription)

        return subscriptions_by_member_and_product_type

    @classmethod
    def build_payments_for_subscriptions_in_trial(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
    ) -> list[Payment]:
        previous_month = (current_month - relativedelta(months=1)).replace(day=1)

        subscriptions_in_trial = cls.get_current_and_renewed_subscriptions(
            cache=cache, first_of_month=previous_month, is_in_trial=True
        )

        subscriptions_by_member_and_product_type = (
            cls.group_subscriptions_by_member_and_product_type(subscriptions_in_trial)
        )

        payments_to_create = []

        for (
            member,
            subscriptions_by_product_type,
        ) in subscriptions_by_member_and_product_type.items():
            for product_type, subscriptions in subscriptions_by_product_type.items():
                payment = (
                    cls.build_payment_for_subscriptions_for_member_and_product_type(
                        member=member,
                        first_of_month=previous_month,
                        subscriptions=subscriptions,
                        product_type=product_type,
                        rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                        cache=cache,
                        generated_payments=generated_payments,
                        in_trial=True,
                    )
                )
                if payment is not None:
                    payments_to_create.append(payment)

        return payments_to_create

    @classmethod
    def get_current_and_renewed_subscriptions(
        cls, cache: dict, first_of_month: datetime.date, is_in_trial: bool
    ) -> list[Subscription]:
        existing_subscriptions = TapirCache.get_all_subscriptions(cache=cache)

        planned_renewed_subscriptions = [
            AutomaticSubscriptionRenewalService.build_renewed_subscription(
                subscription=subscription, cache=cache
            )
            for subscription in AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=first_of_month, cache=cache
            )
        ]
        subscriptions_in_trial = [
            subscription
            for subscription in existing_subscriptions.union(
                planned_renewed_subscriptions
            )
            if TrialPeriodManager.is_subscription_in_trial(
                subscription=subscription, reference_date=first_of_month, cache=cache
            )
            == is_in_trial
        ]
        return subscriptions_in_trial

    @classmethod
    def get_number_of_deliveries_for_full_month_price(cls, delivery_cycle: str):
        if delivery_cycle == NO_DELIVERY[0]:
            return 0
        if delivery_cycle == WEEKLY[0]:
            return 4
        if delivery_cycle == ODD_WEEKS[0] or delivery_cycle == EVEN_WEEKS[0]:
            return 2
        if delivery_cycle == EVERY_FOUR_WEEKS[0]:
            return 1
        raise ImproperlyConfigured("Unknown delivery cycle: " + delivery_cycle)

    @classmethod
    def combine_similar_payments(cls, payments: list[Payment]) -> list[Payment]:
        grouped_payments = cls.group_payments_by_member_and_type_and_due_date(payments)

        combined_payments = []

        for member, payments_by_type in grouped_payments.items():
            for type, payments_by_due_date in payments_by_type.items():
                for due_date, payments in payments_by_due_date.items():
                    if len(payments) == 1:
                        combined_payments.append(payments[0])
                    else:
                        combined_payments.append(cls.combine_payments(payments))

        return combined_payments

    @classmethod
    def group_payments_by_member_and_type_and_due_date(cls, payments: list[Payment]):
        payments_by_member = {}
        for payment in payments:
            if payment.mandate_ref.member not in payments_by_member.keys():
                payments_by_member[payment.mandate_ref.member] = {}
            payments_by_type = payments_by_member[payment.mandate_ref.member]

            if payment.type not in payments_by_type.keys():
                payments_by_type[payment.type] = {}
            payments_by_due_date = payments_by_type[payment.type]

            if payment.due_date not in payments_by_due_date.keys():
                payments_by_due_date[payment.due_date] = []
            payments_by_due_date[payment.due_date].append(payment)

        return payments_by_member

    @classmethod
    def combine_payments(cls, payments: list[Payment]) -> Payment:
        due_date = payments[0].due_date
        mandate_ref = payments[0].mandate_ref
        status = payments[0].status
        payment_type = payments[0].type

        amount = 0
        subscription_payment_range_start = payments[0].subscription_payment_range_start
        subscription_payment_range_end = payments[0].subscription_payment_range_end

        for payment in payments:
            amount += payment.amount
            subscription_payment_range_start = min(
                subscription_payment_range_start,
                payment.subscription_payment_range_start,
            )
            subscription_payment_range_end = max(
                subscription_payment_range_end, payment.subscription_payment_range_end
            )

        return Payment(
            due_date=due_date,
            mandate_ref=mandate_ref,
            status=status,
            type=payment_type,
            amount=amount,
            subscription_payment_range_start=subscription_payment_range_start,
            subscription_payment_range_end=subscription_payment_range_end,
        )
