import datetime

from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
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

        payments_to_create_association_membership = MonthPaymentBuilderAssociationMembership.build_payments_for_association_memberships(
            current_month=first_of_month,
            cache=cache,
            generated_payments=generated_payments,
        )

        payments_to_create_delivery_charges_in_trial = (
            MonthPaymentBuilderDeliveryCharges.build_payments_for_delivery_charges(
                current_month=first_of_month,
                cache=cache,
                generated_payments=generated_payments,
                in_trial=True,
            )
        )

        payments_to_create_delivery_charges_not_in_trial = (
            MonthPaymentBuilderDeliveryCharges.build_payments_for_delivery_charges(
                current_month=first_of_month,
                cache=cache,
                generated_payments=generated_payments.union(
                    payments_to_create_delivery_charges_in_trial
                ),
                in_trial=False,
            )
        )

        return (
            payments_to_create_subscriptions_not_in_trial
            + payments_to_create_subscriptions_in_trial
            + payments_to_create_solidarity_contributions_in_trial
            + payments_to_create_solidarity_contributions_not_in_trial
            + payments_to_create_association_membership
            + payments_to_create_delivery_charges_in_trial
            + payments_to_create_delivery_charges_not_in_trial
        )
