import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import (
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
from tapir.bidding_round.services.bid_validator import BidValidator
from tapir.wirgarten.models import GrowingPeriod, Member, Product, ProductType
from tapir.wirgarten.utils import get_now


class BiddingRoundService:
    EDITABLE_FIELDS = ("name", "comment", "start_at", "end_at")
    SENSITIVE_FIELDS = ("product_type_id", "target_amount_per_year", "prices")

    @classmethod
    @transaction.atomic
    def create_round(
        cls,
        growing_period: GrowingPeriod,
        name: str,
        end_at: datetime.datetime,
        cache: dict,
        start_at: datetime.datetime | None = None,
        comment: str = "",
        product_type_id: str | None = None,
        target_amount_per_year=None,
        prices: list[dict] | None = None,
    ) -> BiddingRound:
        if start_at is not None and start_at > end_at:
            raise ValidationError(
                _("Das Startdatum darf nicht nach dem Enddatum liegen.")
            )

        if product_type_id is None:
            product_types = cls.get_product_types_with_capacity_for_period(
                growing_period, cache=cache
            )
            if len(product_types) != 1:
                raise ValidationError(_("Bitte genau einen Produkttyp auswählen."))
            product_type_id = product_types[0].id

        bidding_round = BiddingRound.objects.create(
            growing_period=growing_period,
            name=name,
            product_type_id=product_type_id,
            start_at=start_at or get_now(cache=cache),
            end_at=end_at,
            comment=comment,
        )
        cls._apply_target_amount_per_year(bidding_round, target_amount_per_year)
        if prices is not None:
            cls._save_round_prices(bidding_round, prices)

        return bidding_round

    @classmethod
    def _apply_target_amount_per_year(cls, bidding_round: BiddingRound, value) -> None:
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
    def _save_round_prices(
        cls, bidding_round: BiddingRound, prices: list[dict]
    ) -> None:
        """Replaces the round's price rows with the given payload.

        The rows are addressed by ``product_id``, so the object ids do not matter and
        the old rows are deleted first.
        """
        if not prices:
            if bidding_round.prices.exists():
                return
            raise ValidationError(
                _("Bitte mindestens ein Produkt mit Preis konfigurieren.")
            )
        valid_product_ids = set(
            Product.objects.filter(
                type_id=bidding_round.product_type_id, deleted=False
            ).values_list("id", flat=True)
        )
        rows_by_product_id = {}
        for entry in prices:
            product_id = entry.get("product_id")
            if product_id is None:
                raise ValidationError(
                    _("Für jeden Preis muss ein Produkt angegeben werden.")
                )
            if product_id not in valid_product_ids:
                raise ValidationError(
                    _(
                        "Es wurde ein Produkt gewählt, das nicht zum Produkttyp der Beitragsrunde gehört."
                    )
                )
            reference_value = AmountParser.parse_optional(entry.get("reference_value"))
            min_amount = AmountParser.parse_optional(entry.get("min_amount"))
            size = AmountParser.parse_optional(entry.get("size"))
            cls._validate_non_negative(
                reference_value, _("Der Richtwert darf nicht negativ sein.")
            )
            cls._validate_non_negative(
                min_amount, _("Der Mindestbetrag darf nicht negativ sein.")
            )
            if size is None or size <= 0:
                raise ValidationError(
                    _("Die Produktgröße ist erforderlich und muss größer als 0 sein.")
                )
            if (
                reference_value is not None
                and min_amount is not None
                and min_amount > reference_value
            ):
                raise ValidationError(
                    _("Der Mindestbetrag darf nicht höher als der Richtwert sein.")
                )
            rows_by_product_id[product_id] = BiddingRoundProductPrice(
                round=bidding_round,
                product_id=product_id,
                reference_value=reference_value,
                min_amount=min_amount,
                size=size,
            )

        bidding_round.prices.all().delete()
        BiddingRoundProductPrice.objects.bulk_create(rows_by_product_id.values())

    @classmethod
    def _validate_non_negative(cls, value, message: str) -> None:
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
                    "Die Beitragsrunde kann nicht wieder geöffnet werden, sobald Verträge erstellt wurden."
                )
            )
        cls._ensure_no_other_active_round(bidding_round)
        bidding_round.status = BIDDING_ROUND_STATUS_ACTIVE
        bidding_round.save()
        return bidding_round

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
    @transaction.atomic
    def update_round_config(
        cls, bidding_round: BiddingRound, changes: dict, cache: dict
    ) -> BiddingRound:
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _(
                    "Die Beitragsrunde kann nach der Vertragserstellung nicht mehr geändert werden."
                )
            )
        cls._validate_round_config_change(bidding_round, changes)

        for field in cls.EDITABLE_FIELDS:
            if field not in changes:
                continue
            if field == "start_at" and changes[field] is None:
                continue
            setattr(bidding_round, field, changes[field])

        new_product_type_id = changes.get("product_type_id")
        if new_product_type_id and new_product_type_id != bidding_round.product_type_id:
            bidding_round.prices.all().delete()
            bidding_round.product_type_id = new_product_type_id

        bidding_round.save()

        if "target_amount_per_year" in changes:
            target_amount_per_year = AmountParser.parse_optional(
                changes["target_amount_per_year"]
            )
            if target_amount_per_year != bidding_round.target_amount_per_year:
                cls._validate_non_negative(
                    target_amount_per_year,
                    _("Der Zielbetrag pro Jahr darf nicht negativ sein."),
                )
                bidding_round.target_amount_per_year = target_amount_per_year
                bidding_round.save(
                    update_fields=["target_amount_per_year", "updated_at"]
                )

        if "prices" in changes and cls._payload_prices_signature(
            changes["prices"]
        ) != cls._prices_signature(bidding_round):
            cls._save_round_prices(bidding_round, changes["prices"])

        return bidding_round

    @classmethod
    def _prices_signature(cls, bidding_round: BiddingRound) -> dict:
        return {
            price.product_id: (
                price.reference_value,
                price.min_amount,
                price.size,
            )
            for price in bidding_round.prices.all()
        }

    @classmethod
    def _payload_prices_signature(cls, prices: list[dict]) -> dict:
        return {
            entry.get("product_id"): (
                AmountParser.parse_optional(entry.get("reference_value")),
                AmountParser.parse_optional(entry.get("min_amount")),
                AmountParser.parse_optional(entry.get("size")),
            )
            for entry in prices
        }

    @classmethod
    def _validate_round_config_change(
        cls, bidding_round: BiddingRound, changes: dict
    ) -> None:
        start_at = changes.get("start_at") or bidding_round.start_at
        end_at = changes.get("end_at", bidding_round.end_at)
        if start_at is not None and end_at is not None and start_at > end_at:
            raise ValidationError(
                _("Das Startdatum darf nicht nach dem Enddatum liegen.")
            )
        if not bidding_round.bids.exists():
            return

        sensitive = (
            changes.get("product_type_id") not in (None, bidding_round.product_type_id)
            or (
                "target_amount_per_year" in changes
                and AmountParser.parse_optional(changes["target_amount_per_year"])
                != bidding_round.target_amount_per_year
            )
            or (
                "prices" in changes
                and cls._payload_prices_signature(changes["prices"])
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
        return BiddingRound.objects.filter(
            start_at__lte=get_now(cache=cache),
            status=BIDDING_ROUND_STATUS_ACTIVE,
            end_at__gte=get_now(cache=cache),
        ).first()

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
    def save_bid(
        cls,
        member: Member,
        bidding_round: BiddingRound,
        bid_input: BidInput,
        cache: dict,
    ) -> Bid:
        """Writes one bid per member and round.

        There is no row lock: a single bid row per member and round means the last
        write wins. Two simultaneous first submits are covered by the unique
        constraint on ``(round, member)``; the lookup is retried on that error.
        """
        bid_input = BidValidator.validate(bidding_round, bid_input, cache=cache)
        values = {
            "product_id": bid_input.product_id,
            "quantity": bid_input.quantity,
            "amount_1": bid_input.amount_1,
        }
        with transaction.atomic():
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
                    update_fields=["product", "quantity", "amount_1", "updated_at"]
                )
        return bid
