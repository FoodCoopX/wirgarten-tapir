import datetime

from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.wirgarten.models import (
    Payment,
)


class MonthPaymentBuilder:
    @classmethod
    def build_payments_for_month(
        cls,
        reference_date: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
    ) -> list[Payment]:
        first_of_month = reference_date.replace(day=1)

        payments_to_create_subscriptions_in_trial = (
            MonthPaymentBuilderSubscriptions.build_payments_for_subscriptions(
                current_month=first_of_month,
                cache=cache,
                generated_payments=generated_payments,
                in_trial=True,
            )
        )

        payments_to_create_subscriptions_not_in_trial = (
            MonthPaymentBuilderSubscriptions.build_payments_for_subscriptions(
                current_month=first_of_month,
                cache=cache,
                generated_payments=generated_payments.union(
                    payments_to_create_subscriptions_in_trial
                ),
                in_trial=False,
            )
        )

        payments_to_create_solidarity_contributions_in_trial = MonthPaymentBuilderSolidarityContributions.build_payments_for_solidarity_contributions(
            current_month=first_of_month,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=True,
        )

        payments_to_create_solidarity_contributions_not_in_trial = MonthPaymentBuilderSolidarityContributions.build_payments_for_solidarity_contributions(
            current_month=first_of_month,
            cache=cache,
            generated_payments=generated_payments.union(
                payments_to_create_solidarity_contributions_in_trial
            ),
            in_trial=False,
        )

        return (
            payments_to_create_subscriptions_not_in_trial
            + payments_to_create_subscriptions_in_trial
            + payments_to_create_solidarity_contributions_in_trial
            + payments_to_create_solidarity_contributions_not_in_trial
        )

    @classmethod
    def combine_similar_payments(cls, payments: list[Payment]) -> list[Payment]:
        grouped_payments = cls.group_payments_by_member_and_type_and_due_date(payments)

        combined_payments = []

        for member, payments_by_type in grouped_payments.items():
            for _, payments_by_due_date in payments_by_type.items():
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
