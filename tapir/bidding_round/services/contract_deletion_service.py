from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.utils import get_now


class BiddingRoundContractDeletionService:
    """Deletes the contracts created by a bidding round and reverts the price/contribution
    adjustments applied to auto-renewers, so the round can be re-run.

    The revert follows the previous-period logic: a renewed subscription's
    price_override was not inherited from the previous season (it is the standard
    price), so it is reset to None; solidarity contributions created for the round's
    period are deleted, which restores the previous period's contribution.
    """

    @classmethod
    def delete_contracts(cls, bidding_round, actor, cache):
        if bidding_round.contracts_created_at is None:
            raise ValidationError(
                _("No contracts have been created for this bidding round.")
            )

        with transaction.atomic():
            subscription_ids = list(
                bidding_round.created_subscriptions.values_list(
                    "subscription_id", flat=True
                )
            )
            Subscription.objects.filter(id__in=subscription_ids).delete()
            bidding_round.created_subscriptions.all().delete()

            cls._revert_non_bidder_contributions(bidding_round, cache=cache)

            bidding_round.contracts_created_at = None
            bidding_round.save(update_fields=["contracts_created_at", "updated_at"])
        return bidding_round

    @classmethod
    def _revert_non_bidder_contributions(cls, bidding_round, cache) -> None:
        product_type_ids = set(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        period = bidding_round.growing_period

        try:
            renewing_subscriptions = AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=period.start_date, cache=cache
            )
        except KeyError:
            renewing_subscriptions = []

        member_ids = {
            subscription.member_id
            for subscription in renewing_subscriptions
            if subscription.product.type_id in product_type_ids
            and subscription.member_id not in bid_member_ids
        }

        for member_id in member_ids:
            SolidarityContribution.objects.filter(
                member_id=member_id, start_date__gte=period.start_date
            ).delete()
