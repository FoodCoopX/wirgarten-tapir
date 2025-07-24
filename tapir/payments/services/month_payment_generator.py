import datetime
from decimal import Decimal

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Subscription, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref


class MonthPaymentGenerator:
    @classmethod
    def generate_payments_for_month(cls, reference_date: datetime.date, cache: dict):
        reference_date = reference_date.replace(day=1)
        existing_payments_no_trial, payments_to_create_no_trial = (
            cls.generate_payments_for_subscriptions_not_in_trial(
                reference_date=reference_date, cache=cache
            )
        )

        existing_payments_trial, payments_to_create_trial = (
            cls.generate_payments_for_subscriptions_in_trial(
                reference_date=reference_date, cache=cache
            )
        )

        created_payments = Payment.objects.bulk_create(
            payments_to_create_no_trial + payments_to_create_trial
        )

        return existing_payments_no_trial + existing_payments_trial + created_payments

    @classmethod
    def generate_payments_for_subscriptions_not_in_trial(
        cls, reference_date: datetime.date, cache: dict
    ):
        subscriptions = cls.get_subscriptions_not_in_trial_that_should_get_a_payment(
            reference_date=reference_date, cache=cache
        )
        subscriptions_by_member_and_product_type = (
            cls.group_subscriptions_by_member_and_product_type(subscriptions)
        )

        payments_due_date = cls.get_payment_due_date_on_month(
            reference_date=reference_date, cache=cache
        )

        existing_payments = []
        payments_to_create = []

        for (
            member,
            subscriptions_by_product_type,
        ) in subscriptions_by_member_and_product_type.items():
            mandate_ref = get_or_create_mandate_ref(member=member, cache=cache)
            for product_type, subscriptions in subscriptions_by_product_type:
                existing_payments = list(
                    Payment.objects.filter(
                        mandate_ref=mandate_ref,
                        due_date=payments_due_date,
                        type=product_type.name,
                    )
                )
                if len(existing_payments) > 0:
                    existing_payments.extend(existing_payments)
                    continue

                amount = sum(
                    subscription.total_price(cache=cache)
                    for subscription in subscriptions
                )
                raise NotImplementedError("Multiply amount by the number of months")

                payments_to_create.append(
                    Payment.objects.create(
                        due_date=payments_due_date,
                        amount=Decimal(amount).quantize(Decimal("0.01")),
                        mandate_ref=mandate_ref,
                        status=Payment.PaymentStatus.DUE,
                        type=product_type.name,
                    )
                )

        return existing_payments, payments_to_create

    @classmethod
    def get_payment_due_date_on_month(cls, reference_date: datetime.date, cache: dict):
        return reference_date.replace(
            day=get_parameter_value(ParameterKeys.PAYMENT_DUE_DAY, cache=cache)
        )

    @classmethod
    def group_subscriptions_by_member_and_product_type(
        cls, subscriptions: list[Subscription]
    ):
        subscriptions_by_member_and_product_type = {}
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
                subscriptions_by_product_type[subscription.product.type] = []

            subscriptions_by_product_type[subscription.product.type].append(
                subscription
            )

        return subscriptions_by_member_and_product_type

    @classmethod
    def get_subscriptions_not_in_trial_that_should_get_a_payment(
        cls, reference_date: datetime.date, cache: dict
    ):
        subscriptions_active_this_month = Subscription.objects.filter(
            start_date__lte=reference_date, end_date__gte=reference_date
        ).select_related("member", "product__type")
        subscriptions_active_and_not_in_trial = [
            subscription
            for subscription in subscriptions_active_this_month
            if not TrialPeriodManager.is_subscription_in_trial(
                subscription=subscription, reference_date=reference_date, cache=cache
            )
        ]

        subscriptions_that_should_get_a_payment = []
        for subscription in subscriptions_active_and_not_in_trial:
            rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                member=subscription.member, reference_date=reference_date, cache=cache
            )
            if MemberPaymentRhythmService.should_generate_payment_at_date(
                rhythm=rhythm, reference_date=reference_date, cache=cache
            ):
                subscriptions_that_should_get_a_payment.append(subscription)
        return subscriptions_that_should_get_a_payment

    @classmethod
    def generate_payments_for_subscriptions_in_trial(
        cls, reference_date: datetime.date, cache: dict
    ):
        raise NotImplementedError("TODO")
        return [], []
