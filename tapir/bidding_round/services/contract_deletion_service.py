import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.models import BiddingRound
from tapir.bidding_round.services.round_contribution_service import (
    RoundContributionService,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.utils import get_now

logger = logging.getLogger(__name__)


class BiddingRoundContractDeletionService:
    """Restore the contracts and contribution changes recorded for this round."""

    @classmethod
    @transaction.atomic
    def delete_contracts(cls, bidding_round, actor, cache):
        bidding_round = BiddingRound.objects.select_for_update().get(
            pk=bidding_round.pk
        )
        if bidding_round.contracts_created_at is None:
            raise ValidationError(
                _("Für diese Beitragsrunde wurden noch keine Verträge erstellt.")
            )

        if not bidding_round.contribution_changes_tracked:
            raise ValidationError(
                _(
                    "Für diese Runde fehlt der frühere Solidaritätsbeitragsstand. Bitte die Rücknahme manuell prüfen."
                )
            )

        RoundContributionService.restore_contributions(bidding_round, cache=cache)
        subscription_ids = list(
            bidding_round.created_subscriptions.values_list(
                "subscription_id", flat=True
            )
        )
        Subscription.objects.filter(id__in=subscription_ids).delete()
        bidding_round.created_subscriptions.all().delete()

        cls._restore_replaced_subscriptions(bidding_round)

        bidding_round.contribution_changes_tracked = False
        bidding_round.contracts_created_at = None
        bidding_round.save(
            update_fields=[
                "contracts_created_at",
                "contribution_changes_tracked",
                "updated_at",
            ]
        )
        logger.info(
            "Bidding round %s contracts deleted by %s: %s subscriptions removed",
            bidding_round.id,
            getattr(actor, "id", actor),
            len(subscription_ids),
        )
        return bidding_round

    @classmethod
    def _restore_replaced_subscriptions(cls, bidding_round) -> None:
        """Recreates everything that contract creation replaced and deleted."""
        for snapshot in bidding_round.replaced_subscriptions.all():
            snapshot.restore()
            snapshot.delete()
