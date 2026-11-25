import datetime
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
    BIDDING_ROUND_STATUS_CONFIGURATION,
)
from tapir.bidding_round.models import (
    Bid,
    BiddingRound,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.services.amount_parser import AmountParser
from tapir.bidding_round.services.bid_input import BidInput
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.bid_validator import BidValidator
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.wirgarten.models import GrowingPeriod, Member, Product, ProductType
from tapir.wirgarten.utils import get_now


@dataclass(frozen=True)
class RoundPriceInput:
    product_id: str
    reference_value: Decimal | None
    min_amount: Decimal | None
    size: Decimal | None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "RoundPriceInput":
        return cls(
            product_id=str(payload.get("product_id") or ""),
            reference_value=AmountParser.parse_optional(payload.get("reference_value")),
            min_amount=AmountParser.parse_optional(payload.get("min_amount")),
            size=AmountParser.parse_optional(payload.get("size")),
        )


@dataclass(frozen=True)
class BiddingRoundConfigChanges:
    name: str | None = None
    comment: str | None = None
    start_at: datetime.datetime | None = None
    end_at: datetime.datetime | None = None
    product_type_id: str | None = None
    target_amount_per_year: Decimal | str | None = None
    prices: list[RoundPriceInput] | None = None
    bidding_procedure: str | None = None
    bid_levels: int | None = None
    include_auto_renewed: bool | None = None
    provided_fields: frozenset[str] = frozenset()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "BiddingRoundConfigChanges":
        prices = None
        if "prices" in payload:
            prices = [
                RoundPriceInput.from_mapping(entry) for entry in payload["prices"]
            ]
        return cls(
            name=payload.get("name"),
            comment=payload.get("comment"),
            start_at=payload.get("start_at"),
            end_at=payload.get("end_at"),
            product_type_id=payload.get("product_type_id"),
            target_amount_per_year=payload.get("target_amount_per_year"),
            prices=prices,
            bidding_procedure=payload.get("bidding_procedure"),
            bid_levels=payload.get("bid_levels"),
            include_auto_renewed=payload.get("include_auto_renewed"),
            provided_fields=frozenset(payload.keys()),
        )


class BiddingRoundService:
    @classmethod
    def validate_round_creation(
        cls,
        end_at: datetime.datetime,
        start_at: datetime.datetime | None = None,
        bidding_procedure: str = BIDDING_ROUND_PROCEDURE_SIMPLE,
        bid_levels: int = 1,
    ) -> None:
        if start_at is not None and start_at > end_at:
            raise ValidationError(
                _("Das Startdatum darf nicht nach dem Enddatum liegen.")
            )
        cls._validate_procedure(bidding_procedure, bid_levels)

    @classmethod
    @transaction.atomic
    def create_round(
        cls,
        growing_period: GrowingPeriod,
        name: str,
        end_at: datetime.datetime,
        cache: dict,
        product_type_id: str,
        start_at: datetime.datetime | None = None,
        comment: str = "",
        target_amount_per_year: Decimal | str | None = None,
        prices: list[RoundPriceInput] | None = None,
        bidding_procedure: str = BIDDING_ROUND_PROCEDURE_SIMPLE,
        bid_levels: int = 1,
        include_auto_renewed: bool = True,
    ) -> BiddingRound:
        if prices is not None:
            cls.validate_round_prices(prices, product_type_id)
        bidding_round = BiddingRound.objects.create(
            growing_period=growing_period,
            name=name,
            product_type_id=product_type_id,
            start_at=start_at or get_now(cache=cache),
            end_at=end_at,
            comment=comment,
            bidding_procedure=bidding_procedure,
            bid_levels=bid_levels,
            include_auto_renewed=include_auto_renewed,
        )
        cls._apply_target_amount_per_year(bidding_round, target_amount_per_year)
        if prices is not None:
            cls._save_round_prices(bidding_round, prices)

        return bidding_round

    @classmethod
    def _validate_procedure(cls, bidding_procedure: str, bid_levels: int) -> None:
        if bidding_procedure not in (
            BIDDING_ROUND_PROCEDURE_SIMPLE,
            BIDDING_ROUND_PROCEDURE_BID_RANGE,
        ):
            raise ValidationError(_("Unbekanntes Verfahren."))
        if bid_levels < 1 or bid_levels > 3:
            raise ValidationError(_("Es sind ein bis drei Gebotsstufen erlaubt."))
        if bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE and bid_levels != 2:
            raise ValidationError(
                _("Das Verfahren mit Gebotsspanne verwendet immer zwei Gebotsstufen.")
            )

    @classmethod
    def _apply_target_amount_per_year(
        cls, bidding_round: BiddingRound, value: Decimal | str | None
    ) -> None:
        if value in (None, ""):
            return
        target_amount_per_year = AmountParser.parse_optional(value)
        cls._validate_non_negative(
            target_amount_per_year,
            _("Der Zielbetrag pro Jahr darf nicht negativ sein."),
        )
        bidding_round.target_amount_per_year = target_amount_per_year
        bidding_round.save(update_fields=["target_amount_per_year", "updated_at"])

    @classmethod
    def validate_round_prices(
        cls,
        prices: list[RoundPriceInput],
        product_type_id: str,
        allow_empty: bool = False,
    ) -> None:
        if not prices:
            if allow_empty:
                return
            raise ValidationError(
                _("Bitte mindestens ein Produkt mit Preis konfigurieren.")
            )
        valid_product_ids = set(
            Product.objects.filter(type_id=product_type_id, deleted=False).values_list(
                "id", flat=True
            )
        )
        for price in prices:
            if not price.product_id:
                raise ValidationError(
                    _("Für jeden Preis muss ein Produkt angegeben werden.")
                )
            if price.product_id not in valid_product_ids:
                raise ValidationError(
                    _(
                        "Das gewählte Produkt gehört nicht zum Produkttyp der Beitragsrunde."
                    )
                )
            cls._validate_non_negative(
                price.reference_value, _("Der Richtwert darf nicht negativ sein.")
            )
            cls._validate_non_negative(
                price.min_amount, _("Der Mindestbetrag darf nicht negativ sein.")
            )
            if price.size is None or price.size <= 0:
                raise ValidationError(_("Die Größe muss größer als 0 sein."))
            if (
                price.reference_value is not None
                and price.min_amount is not None
                and price.min_amount > price.reference_value
            ):
                raise ValidationError(
                    _("Der Mindestbetrag darf nicht größer als der Richtwert sein.")
                )

    @classmethod
    def _save_round_prices(
        cls, bidding_round: BiddingRound, prices: list[RoundPriceInput]
    ) -> None:
        """Replaces the round's price rows with already validated values.

        The caller validates the new values first. The old rows are deleted before
        the new rows are inserted, so the unique product constraint cannot collide.
        """
        if not prices:
            return
        rows_by_product_id = {
            price.product_id: BiddingRoundProductPrice(
                round=bidding_round,
                product_id=price.product_id,
                reference_value=price.reference_value,
                min_amount=price.min_amount,
                size=price.size,
            )
            for price in prices
        }
        bidding_round.prices.all().delete()
        BiddingRoundProductPrice.objects.bulk_create(rows_by_product_id.values())

    @classmethod
    def _validate_non_negative(cls, value: Decimal | None, message: str) -> None:
        if value is not None and value < 0:
            raise ValidationError(message)

    @classmethod
    def _ensure_no_other_active_round(cls, bidding_round: BiddingRound) -> None:
        if (
            BiddingRound.objects.filter(status=BIDDING_ROUND_STATUS_ACTIVE)
            .exclude(pk=bidding_round.pk)
            .exists()
        ):
            raise ValidationError(_("Es ist bereits eine andere Beitragsrunde aktiv."))

    @classmethod
    def start_round(cls, bidding_round: BiddingRound, cache: dict) -> BiddingRound:
        if bidding_round.status != BIDDING_ROUND_STATUS_CONFIGURATION:
            raise ValidationError(
                _("Nur Beitragsrunden im Status Konfiguration können gestartet werden.")
            )
        if bidding_round.target_amount_per_year is None:
            raise ValidationError(
                _("Vor dem Start der Runde ist ein Zielbetrag pro Jahr erforderlich.")
            )
        if not bidding_round.prices.filter(size__gt=0).exists():
            raise ValidationError(
                _(
                    "Vor dem Start der Runde muss mindestens ein Produkt mit Preis und Größe konfiguriert sein."
                )
            )
        cls._ensure_no_other_active_round(bidding_round)
        bidding_round.status = BIDDING_ROUND_STATUS_ACTIVE
        bidding_round.save()
        return bidding_round

    @classmethod
    def close_round(cls, bidding_round: BiddingRound, cache: dict) -> BiddingRound:
        if bidding_round.status != BIDDING_ROUND_STATUS_ACTIVE:
            raise ValidationError(
                _("Nur aktive Beitragsrunden können geschlossen werden.")
            )
        bidding_round.status = BIDDING_ROUND_STATUS_CLOSED
        bidding_round.save()
        return bidding_round

    @classmethod
    def reopen_round(cls, bidding_round: BiddingRound, cache: dict) -> BiddingRound:
        if bidding_round.status != BIDDING_ROUND_STATUS_CLOSED:
            raise ValidationError(
                _("Nur geschlossene Beitragsrunden können wieder geöffnet werden.")
            )
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _(
                    "Eine Beitragsrunde kann nicht wieder geöffnet werden, sobald Verträge erstellt wurden."
                )
            )
        cls._ensure_no_other_active_round(bidding_round)
        bidding_round.status = BIDDING_ROUND_STATUS_ACTIVE
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
        if bidding_round.status != BIDDING_ROUND_STATUS_CLOSED:
            raise ValidationError(
                _(
                    "Das durchschnittliche Gebot kann erst nach Ende der Beitragsrunde fixiert werden."
                )
            )

        surcharge = Decimal(str(surcharge_percent or 0))
        if surcharge < 0 or surcharge > 100:
            raise ValidationError(
                _("Der Aufschlag muss zwischen 0 und 100 Prozent liegen.")
            )
        position = BiddingRoundStatsService.clamp_position(position)
        with transaction.atomic():
            locked = BiddingRound.objects.select_for_update().get(pk=bidding_round.pk)
            if locked.average_bid_locked_at is not None:
                raise ValidationError(
                    _("Das durchschnittliche Gebot ist bereits fixiert.")
                )
            amounts = BiddingRoundStatsService.build_locked_average_bid(
                bidding_round=locked,
                position=position,
                surcharge_percent=surcharge,
                surcharge_on_bids=bool(surcharge_on_bids),
                surcharge_on_average=bool(surcharge_on_average),
                cache=cache,
            )
            locked.average_bid_locked_at = get_now(cache=cache)
            locked.locked_bid_range_position = position
            locked.locked_surcharge_percent = surcharge
            locked.locked_surcharge_on_bids = bool(surcharge_on_bids)
            locked.locked_surcharge_on_average = bool(surcharge_on_average)
            locked.locked_bidder_average_per_share_per_month = amounts[
                "bidder_amount_per_share_per_month"
            ]
            locked.save()
        bidding_round.refresh_from_db()
        return bidding_round

    @classmethod
    def unlock_average_bid(
        cls, bidding_round: BiddingRound, cache: dict
    ) -> BiddingRound:
        with transaction.atomic():
            locked = BiddingRound.objects.select_for_update().get(pk=bidding_round.pk)
            if locked.average_bid_locked_at is None:
                raise ValidationError(
                    _("Das durchschnittliche Gebot ist nicht fixiert.")
                )
            if locked.contracts_created_at is not None:
                raise ValidationError(
                    _(
                        "Das durchschnittliche Gebot kann nach der Vertragserzeugung nicht mehr freigegeben werden."
                    )
                )
            locked.average_bid_locked_at = None
            locked.locked_bid_range_position = None
            locked.locked_surcharge_percent = Decimal("0")
            locked.locked_surcharge_on_bids = False
            locked.locked_surcharge_on_average = False
            locked.locked_bidder_average_per_share_per_month = None
            locked.save()
        bidding_round.refresh_from_db()
        return bidding_round

    @classmethod
    def confirm_bids(cls, bidding_round: BiddingRound, bid_ids, cache: dict) -> int:
        bids = bidding_round.bids.all()
        if bid_ids:
            bids = bids.filter(id__in=bid_ids)
        return bids.update(admin_confirmed=get_now(cache=cache))

    @classmethod
    def save_admin_bid(
        cls,
        bidding_round: BiddingRound,
        member: Member,
        cache: dict,
        bid_input: BidInput | None = None,
        entered_by_admin: bool | None = None,
        admin_confirmed: bool | None = None,
    ) -> Bid:
        """Creates or updates a bid on behalf of a member."""
        with transaction.atomic():
            locked_round = BiddingRound.objects.select_for_update().get(
                pk=bidding_round.pk
            )
            if locked_round.average_bid_locked_at is not None:
                raise ValidationError(
                    _(
                        "Gebote können nach dem Fixieren des Durchschnittsgebots nicht mehr geändert werden."
                    )
                )
            if locked_round.contracts_created_at is not None and bid_input is not None:
                raise ValidationError(
                    _(
                        "Gebote können nach der Vertragserzeugung nicht mehr geändert werden."
                    )
                )
            values = {}
            if bid_input is not None:
                bid_input = BidValidator.validate_admin_edit(
                    locked_round, bid_input, cache=cache
                )
                values = {
                    "product_id": bid_input.product_id,
                    "quantity": bid_input.quantity,
                    "amount_1": bid_input.amount_1,
                    "amount_2": bid_input.amount_2,
                    "amount_3": bid_input.amount_3,
                }

            bid, created = Bid.objects.get_or_create(
                member=member, round=locked_round, defaults=values
            )
            if entered_by_admin is not None:
                bid.entered_by_admin = entered_by_admin
            if admin_confirmed is not None:
                bid.admin_confirmed = get_now(cache=cache) if admin_confirmed else None
            if not created:
                for field, value in values.items():
                    setattr(bid, field, value)
            bid.save()
        return bid

    @classmethod
    def delete_round(cls, bidding_round: BiddingRound, cache: dict) -> None:
        if bidding_round.status not in (
            BIDDING_ROUND_STATUS_CONFIGURATION,
            BIDDING_ROUND_STATUS_CLOSED,
        ):
            raise ValidationError(
                _(
                    "Beitragsrunden können nur im Status Konfiguration oder Abgeschlossen gelöscht werden."
                )
            )
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _(
                    "Die Beitragsrunde kann nicht gelöscht werden, sobald Verträge erstellt wurden."
                )
            )
        bidding_round.delete()

    @classmethod
    def update_round_config(
        cls,
        bidding_round: BiddingRound,
        changes: BiddingRoundConfigChanges,
        cache: dict,
    ) -> BiddingRound:
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _(
                    "Die Beitragsrunde kann nach der Vertragserstellung nicht mehr geändert werden."
                )
            )
        cls.validate_round_config_change(bidding_round, changes)
        if changes.prices is not None:
            cls.validate_round_prices(
                changes.prices,
                changes.product_type_id or bidding_round.product_type_id,
                allow_empty=bidding_round.prices.exists(),
            )
        return cls._apply_round_config_change(bidding_round, changes, cache)

    @classmethod
    @transaction.atomic
    def _apply_round_config_change(
        cls,
        bidding_round: BiddingRound,
        changes: BiddingRoundConfigChanges,
        cache: dict,
    ) -> BiddingRound:
        if "name" in changes.provided_fields and changes.name is not None:
            bidding_round.name = changes.name
        if "comment" in changes.provided_fields and changes.comment is not None:
            bidding_round.comment = changes.comment
        if "start_at" in changes.provided_fields and changes.start_at is not None:
            bidding_round.start_at = changes.start_at
        if "end_at" in changes.provided_fields and changes.end_at is not None:
            bidding_round.end_at = changes.end_at
        if (
            "bidding_procedure" in changes.provided_fields
            and changes.bidding_procedure is not None
        ):
            bidding_round.bidding_procedure = changes.bidding_procedure
        if "bid_levels" in changes.provided_fields and changes.bid_levels is not None:
            bidding_round.bid_levels = changes.bid_levels
        if (
            "include_auto_renewed" in changes.provided_fields
            and changes.include_auto_renewed is not None
        ):
            bidding_round.include_auto_renewed = changes.include_auto_renewed
        if (
            "product_type_id" in changes.provided_fields
            and changes.product_type_id is not None
        ):
            if changes.product_type_id != bidding_round.product_type_id:
                bidding_round.prices.all().delete()
            bidding_round.product_type_id = changes.product_type_id
        bidding_round.save()

        if "target_amount_per_year" in changes.provided_fields:
            target_amount_per_year = AmountParser.parse_optional(
                changes.target_amount_per_year
            )
            cls._validate_non_negative(
                target_amount_per_year,
                _("Der Zielbetrag pro Jahr darf nicht negativ sein."),
            )
            if target_amount_per_year != bidding_round.target_amount_per_year:
                bidding_round.target_amount_per_year = target_amount_per_year
                bidding_round.save(
                    update_fields=["target_amount_per_year", "updated_at"]
                )

        if "prices" in changes.provided_fields and changes.prices is not None:
            if cls._payload_prices_signature(changes.prices) != cls._prices_signature(
                bidding_round
            ):
                cls._save_round_prices(bidding_round, changes.prices)

        return bidding_round

    @classmethod
    def _prices_signature(
        cls, bidding_round: BiddingRound
    ) -> dict[str, tuple[Decimal | None, Decimal | None, Decimal | None]]:
        return {
            price.product_id: (
                price.reference_value,
                price.min_amount,
                price.size,
            )
            for price in bidding_round.prices.all()
        }

    @classmethod
    def _payload_prices_signature(
        cls, prices: list[RoundPriceInput]
    ) -> dict[str, tuple[Decimal | None, Decimal | None, Decimal | None]]:
        return {
            price.product_id: (
                price.reference_value,
                price.min_amount,
                price.size,
            )
            for price in prices
        }

    @classmethod
    def validate_round_config_change(
        cls, bidding_round: BiddingRound, changes: BiddingRoundConfigChanges
    ) -> None:
        start_at = (
            changes.start_at
            if "start_at" in changes.provided_fields
            else bidding_round.start_at
        )
        end_at = (
            changes.end_at
            if "end_at" in changes.provided_fields
            else bidding_round.end_at
        )
        if start_at is not None and end_at is not None and start_at > end_at:
            raise ValidationError(
                _("Das Startdatum darf nicht nach dem Enddatum liegen.")
            )
        cls._validate_procedure(
            (
                changes.bidding_procedure
                if "bidding_procedure" in changes.provided_fields
                else bidding_round.bidding_procedure
            ),
            (
                changes.bid_levels
                if "bid_levels" in changes.provided_fields
                else bidding_round.bid_levels
            ),
        )

        if not bidding_round.bids.exists():
            return

        sensitive = (
            (
                "product_type_id" in changes.provided_fields
                and changes.product_type_id not in (None, bidding_round.product_type_id)
            )
            or (
                "target_amount_per_year" in changes.provided_fields
                and AmountParser.parse_optional(changes.target_amount_per_year)
                != bidding_round.target_amount_per_year
            )
            or (
                "prices" in changes.provided_fields
                and changes.prices is not None
                and cls._payload_prices_signature(changes.prices)
                != cls._prices_signature(bidding_round)
            )
        )
        if sensitive:
            raise ValidationError(
                _(
                    "Produkttyp und die Werte der Beitragsrunde können nur geändert werden, solange noch keine Gebote abgegeben wurden."
                )
            )

    @classmethod
    def get_current_open_round(cls, cache: dict) -> BiddingRound | None:
        now = get_now(cache=cache)
        return BiddingRound.objects.filter(
            start_at__lte=now,
            status=BIDDING_ROUND_STATUS_ACTIVE,
            end_at__gte=now,
        ).first()

    @classmethod
    def get_product_types_with_capacity_for_period(
        cls, growing_period: GrowingPeriod
    ) -> list[ProductType]:
        return list(
            ProductType.objects.filter(
                productcapacity__period=growing_period,
                productcapacity__capacity__gt=0,
            ).distinct()
        )

    @classmethod
    def save_bid(
        cls,
        member: Member,
        bidding_round: BiddingRound,
        bid_input: BidInput,
        cache: dict,
    ) -> Bid:
        """Writes one bid per member and round.

        There is no row lock: a single bid per member and round means the last
        write wins. Two simultaneous first submits are covered by the unique
        constraint on ``(round, member)``; the lookup is retried on that error.
        """
        bid_input = BidValidator.validate(bidding_round, bid_input, cache=cache)
        values = {
            "product_id": bid_input.product_id,
            "quantity": bid_input.quantity,
            "amount_1": bid_input.amount_1,
            "amount_2": bid_input.amount_2,
            "amount_3": bid_input.amount_3,
        }
        with transaction.atomic():
            if bidding_round.average_bid_locked_at is not None:
                raise ValidationError(
                    _(
                        "Gebote können nach dem Fixieren des Durchschnittsgebots nicht mehr geändert werden."
                    )
                )
            try:
                bid, created = Bid.objects.get_or_create(
                    member=member, round=bidding_round, defaults=values
                )
            except IntegrityError:
                bid, created = (
                    Bid.objects.get(member=member, round=bidding_round),
                    False,
                )
            if not created:
                for field, value in values.items():
                    setattr(bid, field, value)
                bid.save(
                    update_fields=[
                        "product",
                        "quantity",
                        "amount_1",
                        "amount_2",
                        "amount_3",
                        "updated_at",
                    ]
                )
        return bid
