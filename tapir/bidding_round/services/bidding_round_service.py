import datetime
import logging
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.bidding_round.config import ACTIVE, CLOSED, CONFIGURATION
from tapir.bidding_round.models import (
    Bid,
    BidItem,
    BiddingRound,
    BiddingRoundProduct,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.services.bid_validator import BidValidator
from tapir.bidding_round.services.bidding_round_mail_token_builder import (
    BiddingRoundMailTokenBuilder,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import GrowingPeriod, Member, Product, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_now

logger = logging.getLogger(__name__)


class BiddingRoundService:
    EDITABLE_FIELDS = (
        "name",
        "comment",
        "start_at",
        "end_at",
        "include_auto_renewed",
        "bidding_procedure",
        "bid_levels",
    )
    SENSITIVE_FIELDS = (
        "bidding_procedure",
        "bid_levels",
        "product_type_id",
        "target_amount_per_year",
        "prices",
    )

    @classmethod
    def create_round(
        cls,
        growing_period: GrowingPeriod,
        name: str,
        bidding_procedure: str,
        end_at: datetime.datetime,
        cache: dict,
        start_at: datetime.datetime | None = None,
        include_auto_renewed: bool | None = None,
        comment: str = "",
        product_type_id: str | None = None,
        bid_levels: int = 1,
        target_amount_per_year=None,
        prices: list[dict] | None = None,
    ) -> BiddingRound:
        if end_at is None:
            raise ValidationError(_("The bidding round must have an end date."))
        if start_at is not None and start_at > end_at:
            raise ValidationError(_("The start date must not be after the end date."))

        if include_auto_renewed is None:
            include_auto_renewed = get_parameter_value(
                ParameterKeys.BIDDING_ROUND_STATS_INCLUDE_AUTO_RENEWED, cache=cache
            )

        if product_type_id is None:
            product_types = cls.get_product_types_with_capacity_for_period(
                growing_period, cache=cache
            )
            if len(product_types) != 1:
                raise ValidationError(_("Please select exactly one product type."))
            product_type_id = product_types[0].id

        bidding_round = BiddingRound.objects.create(
            growing_period=growing_period,
            name=name,
            bidding_procedure=bidding_procedure,
            bid_levels=bid_levels,
            start_at=start_at or get_now(cache=cache),
            end_at=end_at,
            include_auto_renewed=include_auto_renewed,
            comment=comment,
        )

        round_product, _created = BiddingRoundProduct.objects.get_or_create(
            round=bidding_round, product_type_id=product_type_id
        )
        cls._apply_target_amount_per_year(round_product, target_amount_per_year)
        if prices is not None:
            cls._save_round_prices(round_product, prices)

        return bidding_round

    @classmethod
    def _apply_target_amount_per_year(cls, round_product, value) -> None:
        if value in (None, ""):
            return
        target_amount_per_year = cls._parse_optional_decimal(value)
        cls._validate_non_negative(
            target_amount_per_year,
            _("The target amount per year must not be negative."),
        )
        round_product.target_amount_per_year = target_amount_per_year
        round_product.save(update_fields=["target_amount_per_year"])

    @classmethod
    def _save_round_prices(cls, round_product, prices: list[dict]) -> None:
        valid_product_ids = set(
            Product.objects.filter(
                type_id=round_product.product_type_id, deleted=False
            ).values_list("id", flat=True)
        )
        payload_product_ids = set()
        for entry in prices:
            product_id = entry["product_id"]
            if product_id not in valid_product_ids:
                raise ValidationError(
                    _(
                        "A product was selected that does not belong to the bidding "
                        "round's product type."
                    )
                )
            payload_product_ids.add(product_id)
            reference_value = cls._parse_optional_decimal(entry.get("reference_value"))
            min_amount = cls._parse_optional_decimal(entry.get("min_amount"))
            cls._validate_non_negative(
                reference_value, _("The reference value must not be negative.")
            )
            cls._validate_non_negative(
                min_amount, _("The minimum amount must not be negative.")
            )
            if (
                reference_value is not None
                and min_amount is not None
                and min_amount > reference_value
            ):
                raise ValidationError(
                    _(
                        "The minimum amount must not be higher than the reference "
                        "value."
                    )
                )
            BiddingRoundProductPrice.objects.update_or_create(
                round_product=round_product,
                product_id=product_id,
                defaults={
                    "reference_value": reference_value,
                    "min_amount": min_amount,
                },
            )
        BiddingRoundProductPrice.objects.filter(round_product=round_product).exclude(
            product_id__in=payload_product_ids
        ).delete()

    @classmethod
    def _validate_non_negative(cls, value, message) -> None:
        if value is not None and value < 0:
            raise ValidationError(message)

    @classmethod
    def _ensure_no_other_active_round(cls, bidding_round: BiddingRound) -> None:
        if (
            BiddingRound.objects.filter(status=ACTIVE)
            .exclude(pk=bidding_round.pk)
            .exists()
        ):
            raise ValidationError(_("Another bidding round is already active."))

    @classmethod
    def start_round(cls, bidding_round: BiddingRound, cache: dict) -> BiddingRound:
        if bidding_round.status != CONFIGURATION:
            raise ValidationError(
                _("Only bidding rounds with status configuration can be started.")
            )
        round_product = bidding_round.products.first()
        if round_product is None or round_product.target_amount_per_year is None:
            raise ValidationError(
                _(
                    "A target amount per year is required before the round can be "
                    "started."
                )
            )
        cls._ensure_no_other_active_round(bidding_round)
        bidding_round.status = ACTIVE
        bidding_round.save()
        return bidding_round

    @classmethod
    def close_round(cls, bidding_round: BiddingRound, cache: dict) -> BiddingRound:
        if bidding_round.status != ACTIVE:
            raise ValidationError(_("Only active bidding rounds can be closed."))
        bidding_round.status = CLOSED
        bidding_round.save()
        return bidding_round

    @classmethod
    def reopen_round(cls, bidding_round: BiddingRound, cache: dict) -> BiddingRound:
        if bidding_round.status != CLOSED:
            raise ValidationError(_("Only closed bidding rounds can be reopened."))
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _(
                    "The bidding round can no longer be reopened once contracts have "
                    "been created. Delete the contracts first."
                )
            )
        cls._ensure_no_other_active_round(bidding_round)
        bidding_round.status = ACTIVE
        bidding_round.save()
        return bidding_round

    @classmethod
    def lock_average_bid(
        cls,
        bidding_round: BiddingRound,
        position,
        surcharge_percent,
        surcharge_on_bids,
        surcharge_on_average,
        cache: dict,
    ) -> BiddingRound:
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        surcharge_percent = Decimal(str(surcharge_percent or 0))
        if surcharge_percent < 0 or surcharge_percent > 100:
            raise ValidationError(_("The surcharge must be between 0 and 100 percent."))

        position = BiddingRoundStatsService.clamp_traffic_light_position(position)
        with transaction.atomic():
            locked = BiddingRound.objects.select_for_update().get(pk=bidding_round.pk)
            if locked.average_bid_locked_at is not None:
                raise ValidationError(_("The average bid is already locked."))
            amounts = BiddingRoundStatsService.build_locked_average_bid(
                bidding_round=locked,
                position=position,
                surcharge_percent=surcharge_percent,
                surcharge_on_bids=bool(surcharge_on_bids),
                surcharge_on_average=bool(surcharge_on_average),
                cache=cache,
            )
            locked.average_bid_locked_at = get_now(cache=cache)
            locked.locked_traffic_light_position = position
            locked.locked_surcharge_percent = surcharge_percent
            locked.locked_surcharge_on_bids = bool(surcharge_on_bids)
            locked.locked_surcharge_on_average = bool(surcharge_on_average)
            locked.locked_average_bid_per_share_per_month = amounts[
                "amount_per_share_per_month"
            ]
            locked.locked_average_bid_per_share_per_year = amounts[
                "amount_per_share_per_year"
            ]
            locked.locked_bidder_average_per_share_per_month = amounts[
                "bidder_amount_per_share_per_month"
            ]
            locked.locked_bidder_average_per_share_per_year = amounts[
                "bidder_amount_per_share_per_year"
            ]
            locked.save()
        bidding_round.refresh_from_db()
        logger.info(
            "Bidding round %s average bid locked at position %s (surcharge %s%%)",
            bidding_round.id,
            position,
            surcharge_percent,
        )
        return bidding_round

    @classmethod
    def unlock_average_bid(
        cls, bidding_round: BiddingRound, cache: dict
    ) -> BiddingRound:
        with transaction.atomic():
            locked = BiddingRound.objects.select_for_update().get(pk=bidding_round.pk)
            if locked.average_bid_locked_at is None:
                raise ValidationError(_("The average bid is not locked."))
            if locked.contracts_created_at is not None:
                raise ValidationError(
                    _(
                        "The average bid can no longer be unlocked once contracts have "
                        "been created. Delete the contracts first."
                    )
                )
            locked.average_bid_locked_at = None
            locked.locked_traffic_light_position = None
            locked.locked_surcharge_percent = Decimal("0")
            locked.locked_surcharge_on_bids = False
            locked.locked_surcharge_on_average = False
            locked.locked_average_bid_per_share_per_month = None
            locked.locked_average_bid_per_share_per_year = None
            locked.locked_bidder_average_per_share_per_month = None
            locked.locked_bidder_average_per_share_per_year = None
            locked.save()
        bidding_round.refresh_from_db()
        logger.info("Bidding round %s average bid unlocked", bidding_round.id)
        return bidding_round

    @classmethod
    def delete_round(cls, bidding_round: BiddingRound, cache: dict) -> None:
        if bidding_round.status not in (CONFIGURATION, CLOSED):
            raise ValidationError(
                _(
                    "Bidding rounds can only be deleted with status configuration "
                    "or closed."
                )
            )
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _(
                    "The bidding round can no longer be deleted once contracts have "
                    "been created. Delete the contracts first."
                )
            )
        bidding_round.delete()

    @classmethod
    def update_round_config(
        cls, bidding_round: BiddingRound, changes: dict, cache: dict
    ) -> BiddingRound:
        cls._validate_round_config_change(bidding_round, changes)

        for field in cls.EDITABLE_FIELDS:
            if field in changes:
                setattr(bidding_round, field, changes[field])

        if changes.get("product_type_id"):
            bidding_round.products.all().delete()
            BiddingRoundProduct.objects.create(
                round=bidding_round, product_type_id=changes["product_type_id"]
            )

        bidding_round.save()

        round_product = bidding_round.products.first()
        if round_product is not None:
            if "target_amount_per_year" in changes:
                round_product.target_amount_per_year = cls._parse_optional_decimal(
                    changes["target_amount_per_year"]
                )
                cls._validate_non_negative(
                    round_product.target_amount_per_year,
                    _("The target amount per year must not be negative."),
                )
                round_product.save(update_fields=["target_amount_per_year"])
            if "prices" in changes:
                cls._save_round_prices(round_product, changes["prices"])

        return bidding_round

    @classmethod
    def _validate_round_config_change(
        cls, bidding_round: BiddingRound, changes: dict
    ) -> None:
        if not bidding_round.bids.exists():
            return
        if any(field in changes for field in cls.SENSITIVE_FIELDS):
            raise ValidationError(
                _(
                    "The bidding procedure, the number of bids, the biddable product "
                    "types and the bidding round values can only be changed as long "
                    "as no bids have been placed."
                )
            )

    @classmethod
    def get_current_open_round(cls, cache: dict) -> BiddingRound | None:
        now = get_now(cache=cache)
        return (
            BiddingRound.objects.filter(status=ACTIVE, end_at__gte=now)
            .order_by("end_at")
            .first()
        )

    @classmethod
    def get_product_types_with_capacity_for_period(
        cls, growing_period: GrowingPeriod, cache: dict
    ) -> list[ProductType]:
        return list(
            ProductType.objects.filter(
                productcapacity__period=growing_period,
                productcapacity__capacity__gt=0,
            ).distinct()
        )

    @classmethod
    def get_biddable_product_types_for_round(
        cls, bidding_round: BiddingRound, cache: dict
    ) -> list[ProductType]:
        configured_type_ids = bidding_round.products.values_list(
            "product_type_id", flat=True
        )
        return [
            product_type
            for product_type in cls.get_product_types_with_capacity_for_period(
                bidding_round.growing_period, cache=cache
            )
            if product_type.id not in configured_type_ids
        ]

    @classmethod
    def get_or_create_bid(
        cls, member: Member, bidding_round: BiddingRound, cache: dict
    ) -> Bid:
        bid, _ = Bid.objects.get_or_create(member=member, round=bidding_round)
        return bid

    @classmethod
    def is_pickup_location_change_enabled(cls, cache: dict) -> bool:
        try:
            return get_parameter_value(
                ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED, cache=cache
            )
        except KeyError:
            return False

    @classmethod
    def _parse_optional_decimal(cls, value) -> Decimal | None:
        if value in (None, ""):
            return None
        if isinstance(value, str):
            value = value.strip().replace("€", "").replace(",", ".")
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            raise ValidationError(_("Please enter a valid number."))

    @classmethod
    def _build_bid_item(cls, bid: Bid, item: dict) -> BidItem:
        return BidItem(
            bid=bid,
            round_product_id=item["round_product_id"],
            product_id=item["product_id"],
            quantity=item["quantity"],
            amount_1=cls._parse_optional_decimal(item.get("amount_1")),
            amount_2=cls._parse_optional_decimal(item.get("amount_2")),
            amount_3=cls._parse_optional_decimal(item.get("amount_3")),
        )

    @classmethod
    def _resolve_pickup_location_id(
        cls,
        member: Member,
        bidding_round: BiddingRound,
        pickup_location_id,
        cache: dict,
    ):
        """When changing the pickup location is disabled, the submitted value is
        ignored and the member's current pickup location is kept."""
        if cls.is_pickup_location_change_enabled(cache=cache):
            return pickup_location_id
        from tapir.bidding_round.services.bidding_round_capacity_service import (
            BiddingRoundCapacityService,
        )
        from tapir.pickup_locations.services.member_pickup_location_getter import (
            MemberPickupLocationGetter,
        )

        return MemberPickupLocationGetter.get_member_pickup_location_id(
            member=member,
            reference_date=BiddingRoundCapacityService.get_contract_start_date(
                bidding_round, cache
            ),
        )

    @classmethod
    def save_bid(
        cls,
        member: Member,
        bidding_round: BiddingRound,
        items: list[dict],
        cache: dict,
        pickup_location_id: str | None = None,
    ) -> Bid:
        if not isinstance(member, Member):
            raise ValidationError(_("Only members can place a bid."))

        with transaction.atomic():
            bidding_round = BiddingRound.objects.select_for_update().get(
                pk=bidding_round.pk
            )
            pickup_location_id = cls._resolve_pickup_location_id(
                member, bidding_round, pickup_location_id, cache
            )
            BidValidator.validate(
                bidding_round, items, pickup_location_id, cache=cache, member=member
            )

            bid_exists = Bid.objects.filter(member=member, round=bidding_round).exists()
            bid = cls.get_or_create_bid(member, bidding_round, cache=cache)
            bid.pickup_location_id = pickup_location_id
            bid.save()

            bid.items.all().delete()
            BidItem.objects.bulk_create(
                [cls._build_bid_item(bid, item) for item in items]
            )

        TransactionalTrigger.fire_action(
            trigger_data=TransactionalTriggerData(
                key=(
                    Events.BIDDING_ROUND_BID_RECEIVED
                    if not bid_exists
                    else Events.BIDDING_ROUND_BID_UPDATED
                ),
                recipient_id_in_base_queryset=member.id,
                token_data=BiddingRoundMailTokenBuilder.build_bid_tokens(
                    bid, cache=cache
                ),
            )
        )
        return bid

    @classmethod
    def save_admin_bid(
        cls,
        bidding_round: BiddingRound,
        member: Member,
        cache: dict,
        items: list[dict] | None = None,
        pickup_location_id: str | None = None,
        entered_by_admin: bool | None = None,
        admin_confirmed: bool | None = None,
    ) -> Bid:
        with transaction.atomic():
            locked_round = BiddingRound.objects.select_for_update().get(
                pk=bidding_round.pk
            )
            if items:
                BidValidator.validate_admin_edit(
                    locked_round,
                    items,
                    pickup_location_id,
                    cache=cache,
                    member=member,
                )

            bid, _created = Bid.objects.get_or_create(member=member, round=locked_round)

            if locked_round.contracts_created_at is not None:
                if items is not None:
                    raise ValidationError(
                        _(
                            "Bids can no longer be changed once the contracts have been "
                            "created. Delete the contracts first."
                        )
                    )
                if pickup_location_id is not None and str(pickup_location_id) != str(
                    bid.pickup_location_id
                ):
                    raise ValidationError(
                        _(
                            "The pickup location can no longer be changed once the "
                            "contracts have been created. Delete the contracts first."
                        )
                    )

            bid.pickup_location_id = pickup_location_id
            if entered_by_admin is not None:
                bid.entered_by_admin = entered_by_admin
            if admin_confirmed is not None:
                bid.admin_confirmed = get_now(cache=cache) if admin_confirmed else None
            bid.save()

            if items is not None:
                bid.items.all().delete()
                BidItem.objects.bulk_create(
                    [cls._build_bid_item(bid, item) for item in items]
                )

        return bid
