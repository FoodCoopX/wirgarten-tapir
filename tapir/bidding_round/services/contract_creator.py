import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import CLOSED
from tapir.bidding_round.models import (
    BiddingRoundCreatedSubscription,
    BiddingRoundReplacedSubscription,
)
from tapir.bidding_round.services.bidding_round_capacity_service import (
    BiddingRoundCapacityService,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.non_bidder_contribution_service import (
    NonBidderContributionService,
)
from tapir.payments.services.mandate_reference_provider import (
    MandateReferenceProvider,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.models import Subscription

logger = logging.getLogger(__name__)
from tapir.wirgarten.utils import get_now


class ContractCreator:
    @classmethod
    def create_contracts_from_bids(
        cls,
        bidding_round,
        cache,
        bid_ids=None,
        actor=None,
        bid_level=None,
        create_auto_renewed_contracts=False,
        auto_renewed_member_ids=None,
    ):
        if bidding_round.status != CLOSED:
            raise ValidationError(
                _("Contracts can only be created after the bidding round has ended.")
            )

        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _(
                    "Contracts have already been created for this bidding round. "
                    "Delete them first to create them again."
                )
            )

        if bidding_round.average_bid_locked_at is None:
            raise ValidationError(
                _("The average bid must be locked before contracts can be created.")
            )

        bids = list(bidding_round.bids.select_related("member").all())
        if bid_ids:
            selected_ids = {str(bid_id) for bid_id in bid_ids}
            bids = [bid for bid in bids if str(bid.id) in selected_ids]

        unconfirmed_bids = [bid for bid in bids if bid.admin_confirmed is None]
        if unconfirmed_bids:
            raise ValidationError(
                _(
                    "All selected bids must be confirmed before contracts can be "
                    "created. Still unconfirmed: %(names)s"
                )
                % {"names": ", ".join(str(bid.member) for bid in unconfirmed_bids)}
            )

        if bid_level is not None:
            position = BiddingRoundStatsService.get_level_position(bid_level)
        else:
            position = BiddingRoundStatsService.get_default_position(
                bidding_round, cache=cache
            )

        errors = []
        created_subscriptions = []
        for bid in bids:
            try:
                with transaction.atomic():
                    new_subscriptions = cls._create_contracts_for_bid(
                        bid,
                        bidding_round,
                        actor=actor,
                        cache=cache,
                        position=position,
                    )
                created_subscriptions.extend(new_subscriptions)
            except ValidationError as error:
                errors.append(
                    {
                        "bid_id": bid.id,
                        "member": bid.member,
                        "error": str(error),
                        "product_name": cls._get_bid_product_type_names(bid),
                    }
                )

        if create_auto_renewed_contracts:
            created_subscriptions.extend(
                cls._create_auto_renewed_contracts(
                    bidding_round,
                    actor=actor,
                    cache=cache,
                    member_ids=auto_renewed_member_ids,
                )
            )

        non_bidder_member_ids = (
            NonBidderContributionService.apply_non_bidder_contributions(
                bidding_round, actor=actor, cache=cache
            )
        )

        # Only mark the round as done when at least one contract was actually created,
        # so a failed run can be retried without unlocking.
        if created_subscriptions:
            bidding_round.contracts_created_at = get_now(cache=cache)
            bidding_round.save(update_fields=["contracts_created_at", "updated_at"])
        logger.info(
            "Bidding round %s contract creation by %s: %s subscriptions created, "
            "%s errors",
            bidding_round.id,
            getattr(actor, "id", actor),
            len(created_subscriptions),
            len(errors),
        )
        return {
            "errors": errors,
            "subscriptions": created_subscriptions,
            "non_bidder_member_ids": non_bidder_member_ids,
        }

    @classmethod
    def _create_auto_renewed_contracts(
        cls, bidding_round, actor, cache, member_ids=None
    ) -> list:
        """
        Materialises the season contracts of auto-renewed members (non-bidders),
        bypassing the notice period. Used when the admin explicitly enables it in the
        create-contracts dialog. If member_ids is given, only those members are created.
        """
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        product_type_ids = set(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        selected_member_ids = (
            {str(member_id) for member_id in member_ids}
            if member_ids is not None
            else None
        )
        try:
            renewing_subscriptions = AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=bidding_round.growing_period.start_date, cache=cache
            )
        except KeyError:
            return []

        created = []
        for subscription in renewing_subscriptions:
            if subscription.member_id in bid_member_ids:
                continue
            if subscription.product.type_id not in product_type_ids:
                continue
            if (
                selected_member_ids is not None
                and subscription.member_id not in selected_member_ids
            ):
                continue
            if Subscription.objects.filter(
                member_id=subscription.member_id,
                period=bidding_round.growing_period,
                product_id=subscription.product_id,
                cancellation_ts__isnull=True,
            ).exists():
                continue
            renewed_subscription = (
                AutomaticSubscriptionRenewalService.build_renewed_subscription(
                    subscription, cache=cache
                )
            )
            if renewed_subscription.period_id != bidding_round.growing_period_id:
                continue
            renewed_subscription.save()
            BiddingRoundCreatedSubscription.objects.create(
                round=bidding_round,
                subscription=renewed_subscription,
                is_bidder_contract=False,
            )
            created.append(renewed_subscription)
        return created

    @classmethod
    def check_contracts_from_bids(cls, bidding_round, cache, bid_ids=None) -> list:
        """
        Pre-check: returns one entry per bid that cannot be turned into a contract,
        without writing anything. Used to show the affected members before creating.
        """
        bids = list(bidding_round.bids.select_related("member").all())
        if bid_ids:
            selected_ids = {str(bid_id) for bid_id in bid_ids}
            bids = [bid for bid in bids if str(bid.id) in selected_ids]

        errors = []
        for bid in bids:
            try:
                cls._check_capacity(bid, cache=cache)
            except ValidationError as error:
                errors.append(
                    {
                        "bid_id": bid.id,
                        "member": bid.member,
                        "error": str(error),
                        "product_name": cls._get_bid_product_type_names(bid),
                    }
                )
        return errors

    @classmethod
    def _get_bid_product_type_names(cls, bid) -> str:
        return ", ".join(
            sorted(
                {
                    item.product.type.name
                    for item in bid.items.select_related("product__type").all()
                }
            )
        )

    @classmethod
    def _get_item_amount(cls, item, bidding_round, cache, position):
        return BiddingRoundStatsService.get_effective_amount(
            item, bidding_round, cache=cache, position=position
        )

    @classmethod
    def _create_contracts_for_bid(cls, bid, bidding_round, actor, cache, position):
        period = bidding_round.growing_period

        cls._check_capacity(bid, cache=cache)

        new_subscriptions = []
        now = get_now(cache=cache)
        own_created_subscription_ids = set(
            bidding_round.created_subscriptions.values_list(
                "subscription_id", flat=True
            )
        )
        for item in bid.items.select_related("product").all():
            replaced = [
                subscription
                for subscription in Subscription.objects.filter(
                    member=bid.member,
                    period=period,
                    product=item.product,
                    cancellation_ts__isnull=True,
                )
                if subscription.id not in own_created_subscription_ids
            ]
            if replaced:
                BiddingRoundReplacedSubscription.capture(bidding_round, replaced)
                Subscription.objects.filter(
                    id__in=[subscription.id for subscription in replaced]
                ).delete()

            subscription = Subscription(
                member=bid.member,
                product=item.product,
                period=period,
                quantity=item.quantity,
                start_date=period.start_date,
                end_date=period.end_date,
                mandate_ref=MandateReferenceProvider.get_or_create_mandate_reference(
                    member=bid.member, cache=cache
                ),
                consent_ts=now,
                withdrawal_consent_ts=now,
                auto_confirmed=now,
                notice_period_duration=NoticePeriodManager.get_notice_period_duration(
                    product_type=item.product.type,
                    growing_period=period,
                    cache=cache,
                ),
                notice_period_unit=NoticePeriodManager.get_notice_period_unit(
                    product_type=item.product.type,
                    growing_period=period,
                    cache=cache,
                ),
            )
            subscription.save()
            BiddingRoundCreatedSubscription.objects.create(
                round=bidding_round,
                subscription=subscription,
                is_bidder_contract=True,
            )
            new_subscriptions.append(subscription)

        cls._assign_solidarity_contribution(
            bid, bidding_round, new_subscriptions, period, actor, cache, position
        )

        if (
            BiddingRoundService.is_pickup_location_change_enabled(cache=cache)
            and bid.pickup_location_id
        ):
            MemberPickupLocationSetter.link_member_to_pickup_location(
                pickup_location_id=bid.pickup_location_id,
                member=bid.member,
                valid_from=period.start_date,
                actor=actor,
                cache=cache,
                send_change_mail=False,
            )

        return new_subscriptions

    @classmethod
    def _check_capacity(cls, bid, cache):
        items = [
            {"product_id": item.product_id, "quantity": item.quantity}
            for item in bid.items.all()
        ]
        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=bid.round,
            items=items,
            pickup_location_id=bid.pickup_location_id,
            member=bid.member,
            cache=cache,
        )
        if not reasons:
            return
        raise ValidationError(
            BiddingRoundCapacityService.build_insufficient_capacity_message(reasons)
        )

    @classmethod
    def _assign_solidarity_contribution(
        cls, bid, bidding_round, new_subscriptions, period, actor, cache, position
    ):
        standard_monthly_total = sum(
            (
                SubscriptionPriceCalculator.get_monthly_price(
                    subscription, reference_date=period.start_date, cache=cache
                )
                for subscription in new_subscriptions
            ),
            Decimal("0"),
        )
        bid_monthly_total = sum(
            (
                cls._get_item_amount(item, bidding_round, cache, position)
                * item.quantity
                for item in bid.items.all()
            ),
            Decimal("0"),
        )
        MemberSolidarityContributionService.assign_contribution_to_member(
            member=bid.member,
            change_date=period.start_date,
            amount=bid_monthly_total - standard_monthly_total,
            cache=cache,
            actor=actor,
        )
