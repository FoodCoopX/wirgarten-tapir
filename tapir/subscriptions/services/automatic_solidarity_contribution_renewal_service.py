import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_next_growing_period


class AutomaticSolidarityContributionRenewalService:
    @classmethod
    def build_renewed_contribution(
        cls, contribution: SolidarityContribution, cache: dict
    ):
        next_growing_period = get_next_growing_period(cache=cache)

        trial_disabled, trial_end_date_override = (
            AutomaticSubscriptionRenewalService.get_renewed_trial_data(
                contribution, cache=cache
            )
        )

        contribution = SolidarityContribution(
            member=contribution.member,
            amount=contribution.amount,
            start_date=next_growing_period.start_date,
            end_date=next_growing_period.end_date,
            trial_disabled=trial_disabled,
            trial_end_date_override=trial_end_date_override,
        )

        return contribution

    @classmethod
    def get_contributions_that_will_be_renewed(
        cls, reference_date: datetime.date, cache: dict
    ) -> set[SolidarityContribution]:
        if not get_parameter_value(ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache):
            return set()

        current_growing_period = TapirCache.get_growing_period_at_date(
            reference_date=reference_date, cache=cache
        )
        if current_growing_period is None:
            return set()

        current_contributions = TapirCache.get_solidarity_contributions_active_at_date(
            current_growing_period.start_date, cache
        )

        member_ids_that_already_have_a_contribution = {
            contribution.member_id for contribution in current_contributions
        }

        end_of_previous_growing_period = (
            current_growing_period.start_date - datetime.timedelta(days=1)
        )
        contributions_from_previous_growing_period = (
            TapirCache.get_solidarity_contributions_active_at_date(
                end_of_previous_growing_period, cache
            )
        )

        return {
            contribution
            for contribution in contributions_from_previous_growing_period
            if contribution.member_id not in member_ids_that_already_have_a_contribution
        }
