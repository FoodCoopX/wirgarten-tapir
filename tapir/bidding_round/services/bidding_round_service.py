import datetime
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.bidding_round.services.amount_parser import AmountParser
from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
    BIDDING_ROUND_STATUS_CONFIGURATION,
)
from tapir.bidding_round.models import (
    Bid,
    BidItem,
    BiddingRound,
    BiddingRoundProductPrice,
    BiddingRoundProductType,
)
from tapir.bidding_round.services.bid_validator import BidValidator
from tapir.bidding_round.services.bidding_round_mail_token_builder import (
    BiddingRoundMailTokenBuilder,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    OrderFeedback,
    Product,
    ProductType,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_now


@dataclass
class BidConsents:
    sepa_allowed: bool = False
    account_owner: str | None = None
    iban: str | None = None
    payment_rhythm: str | None = None
    privacy_policy_read: bool = False
    cancellation_policy_read: bool = False
    contract_accepted: bool = False
    enforce_consents: bool = False


class BiddingRoundService:
    EDITABLE_FIELDS = (
        "name",
        "comment",
        "start_at",
        "end_at",
        "bidding_procedure",
        "bid_levels",
        "include_auto_renewed",
    )
    SENSITIVE_FIELDS = (
        "product_type_id",
        "target_amount_per_year",
        "prices",
        "bidding_procedure",
        "bid_levels",
        "include_auto_renewed",
    )

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
        bidding_procedure: str = BIDDING_ROUND_PROCEDURE_SIMPLE,
        bid_levels: int = 1,
        include_auto_renewed: bool = True,
    ) -> BiddingRound:
        if end_at is None:
            raise ValidationError(_("Die Beitragsrunde braucht ein Enddatum."))
        if start_at is not None and start_at > end_at:
            raise ValidationError(
                _("Das Startdatum darf nicht nach dem Enddatum liegen.")
            )

        cls._validate_procedure(bidding_procedure, bid_levels)

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
            start_at=start_at or get_now(cache=cache),
            end_at=end_at,
            comment=comment,
            bidding_procedure=bidding_procedure,
            bid_levels=bid_levels,
            include_auto_renewed=include_auto_renewed,
        )

        round_product_type, _created = BiddingRoundProductType.objects.get_or_create(
            round=bidding_round, product_type_id=product_type_id
        )
        cls._apply_target_amount_per_year(round_product_type, target_amount_per_year)
        if prices is not None:
            cls._save_round_prices(round_product_type, prices)

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
    def _apply_target_amount_per_year(cls, round_product_type, value) -> None:
        if value in (None, ""):
            return
        target_amount_per_year = AmountParser.parse_optional(value)
        cls._validate_non_negative(
            target_amount_per_year,
            _("Der Zielbetrag pro Jahr darf nicht negativ sein."),
        )
        round_product_type.target_amount_per_year = target_amount_per_year
        round_product_type.save(update_fields=["target_amount_per_year"])

    @classmethod
    def _save_round_prices(cls, round_product_type, prices: list[dict]) -> None:
        if not prices:
            if round_product_type.prices.exists():
                return
            raise ValidationError(
                _("Bitte mindestens ein Produkt mit Preis konfigurieren.")
            )
        valid_product_ids = set(
            Product.objects.filter(
                type_id=round_product_type.product_type_id, deleted=False
            ).values_list("id", flat=True)
        )
        payload_product_ids = set()
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
            payload_product_ids.add(product_id)
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
            BiddingRoundProductPrice.objects.update_or_create(
                round_product_type=round_product_type,
                product_id=product_id,
                defaults={
                    "reference_value": reference_value,
                    "min_amount": min_amount,
                    "size": size,
                },
            )
        BiddingRoundProductPrice.objects.filter(
            round_product_type=round_product_type
        ).exclude(product_id__in=payload_product_ids).delete()

    @classmethod
    def _validate_non_negative(cls, value, message) -> None:
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
        round_product_type = bidding_round.product_types.first()
        if (
            round_product_type is None
            or round_product_type.target_amount_per_year is None
        ):
            raise ValidationError(
                _("Vor dem Start der Runde ist ein Zielbetrag pro Jahr erforderlich.")
            )
        if not round_product_type.prices.filter(size__gt=0).exists():
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
        items: list[dict] | None = None,
        entered_by_admin: bool | None = None,
        admin_confirmed: bool | None = None,
    ) -> Bid:
        """Legt ein Gebot an oder aktualisiert es."""
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
            if items is not None:
                BidValidator.validate_admin_edit(locked_round, items, cache=cache)

            bid, _created = Bid.objects.get_or_create(member=member, round=locked_round)
            if locked_round.contracts_created_at is not None and items is not None:
                raise ValidationError(
                    _(
                        "Gebote können nach der Vertragserzeugung nicht mehr geändert werden."
                    )
                )

            if entered_by_admin is not None:
                bid.entered_by_admin = entered_by_admin
            if admin_confirmed is not None:
                bid.admin_confirmed = get_now(cache=cache) if admin_confirmed else None
            bid.save()

            if items is not None:
                cls._replace_bid_items(bid, items)
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
        cls, bidding_round: BiddingRound, changes: dict, cache: dict
    ) -> BiddingRound:
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _(
                    "Die Beitragsrunde kann nach der Vertragserstellung nicht mehr geändert werden."
                )
            )
        cls._validate_round_config_change(bidding_round, changes)
        cls._validate_procedure(
            changes.get("bidding_procedure", bidding_round.bidding_procedure),
            changes.get("bid_levels", bidding_round.bid_levels),
        )

        for field in cls.EDITABLE_FIELDS:
            if field in changes:
                setattr(bidding_round, field, changes[field])

        current_product_type = bidding_round.product_types.first()
        new_product_type_id = changes.get("product_type_id")
        if new_product_type_id and (
            current_product_type is None
            or current_product_type.product_type_id != new_product_type_id
        ):
            bidding_round.product_types.all().delete()
            BiddingRoundProductType.objects.create(
                round=bidding_round, product_type_id=new_product_type_id
            )

        bidding_round.save()

        round_product_type = bidding_round.product_types.first()
        if round_product_type is not None:
            if "target_amount_per_year" in changes:
                target_amount_per_year = AmountParser.parse_optional(
                    changes["target_amount_per_year"]
                )
                if target_amount_per_year != round_product_type.target_amount_per_year:
                    cls._validate_non_negative(
                        target_amount_per_year,
                        _("Der Zielbetrag pro Jahr darf nicht negativ sein."),
                    )
                    round_product_type.target_amount_per_year = target_amount_per_year
                    round_product_type.save(update_fields=["target_amount_per_year"])
            if "prices" in changes and cls._payload_prices_signature(
                changes["prices"]
            ) != cls._prices_signature(round_product_type):
                cls._save_round_prices(round_product_type, changes["prices"])

        return bidding_round

    @classmethod
    def _prices_signature(cls, round_product_type) -> dict:
        if round_product_type is None:
            return {}
        return {
            price.product_id: (
                price.reference_value,
                price.min_amount,
                price.size,
            )
            for price in round_product_type.prices.all()
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
        start_at = changes.get("start_at", bidding_round.start_at)
        end_at = changes.get("end_at", bidding_round.end_at)
        if start_at is not None and end_at is not None and start_at > end_at:
            raise ValidationError(
                _("Das Startdatum darf nicht nach dem Enddatum liegen.")
            )
        if not bidding_round.bids.exists():
            return

        round_product_type = bidding_round.product_types.first()
        current_product_type_id = (
            round_product_type.product_type_id
            if round_product_type is not None
            else None
        )
        sensitive = (
            changes.get("product_type_id") not in (None, current_product_type_id)
            or (
                "target_amount_per_year" in changes
                and AmountParser.parse_optional(changes["target_amount_per_year"])
                != (
                    round_product_type.target_amount_per_year
                    if round_product_type is not None
                    else None
                )
            )
            or (
                "prices" in changes
                and cls._payload_prices_signature(changes["prices"])
                != cls._prices_signature(round_product_type)
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
        return (
            BiddingRound.objects.filter(
                Q(start_at__isnull=True) | Q(start_at__lte=now),
                status=BIDDING_ROUND_STATUS_ACTIVE,
                end_at__gte=now,
            )
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
    def _replace_bid_items(cls, bid: Bid, items: list[dict]) -> None:
        bid.items.all().delete()
        BidItem.objects.bulk_create(
            [
                BidItem(
                    bid=bid,
                    round_product_type_id=item["round_product_type_id"],
                    product_id=item["product_id"],
                    quantity=item.get("quantity", 1),
                    amount_1=AmountParser.parse_optional(item.get("amount_1")),
                    amount_2=AmountParser.parse_optional(item.get("amount_2")),
                    amount_3=AmountParser.parse_optional(item.get("amount_3")),
                )
                for item in items
            ]
        )

    @classmethod
    def save_bid(
        cls,
        member: Member,
        bidding_round: BiddingRound,
        items: list[dict],
        cache: dict,
        send_mail: bool = True,
        consents: BidConsents | None = None,
        feedback: str | None = None,
    ) -> Bid:
        if not isinstance(member, Member):
            raise ValidationError(_("Nur Mitglieder können ein Gebot abgeben."))
        consents = consents or BidConsents()

        with transaction.atomic():
            bidding_round = BiddingRound.objects.select_for_update().get(
                pk=bidding_round.pk
            )
            if bidding_round.average_bid_locked_at is not None:
                raise ValidationError(
                    _(
                        "Gebote können nach dem Fixieren des Durchschnittsgebots nicht mehr geändert werden."
                    )
                )
            BidValidator.validate(bidding_round, items, cache=cache)
            if consents.enforce_consents:
                cls._validate_member_consents(
                    member=member,
                    privacy_policy_read=consents.privacy_policy_read,
                    cancellation_policy_read=consents.cancellation_policy_read,
                    contract_accepted=consents.contract_accepted,
                    sepa_allowed=consents.sepa_allowed,
                    iban=consents.iban,
                    cache=cache,
                )
            bid, created = Bid.objects.get_or_create(member=member, round=bidding_round)

            cls._replace_bid_items(bid, items)
            cls._apply_member_consents(
                member=member,
                sepa_allowed=consents.sepa_allowed,
                account_owner=consents.account_owner,
                iban=consents.iban,
                payment_rhythm=consents.payment_rhythm,
                privacy_policy_read=consents.privacy_policy_read,
                cancellation_policy_read=consents.cancellation_policy_read,
                bidding_round=bidding_round,
                cache=cache,
            )
            if feedback:
                OrderFeedback.objects.update_or_create(
                    member=member,
                    bidding_round=bidding_round,
                    defaults={"feedback_text": feedback},
                )

        if send_mail:
            TransactionalTrigger.fire_action(
                trigger_data=TransactionalTriggerData(
                    key=(
                        Events.BIDDING_ROUND_BID_RECEIVED
                        if created
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
    def _validate_member_consents(
        cls,
        member,
        privacy_policy_read: bool,
        cancellation_policy_read: bool,
        contract_accepted: bool,
        sepa_allowed: bool,
        iban: str | None,
        cache: dict,
    ) -> None:
        if not privacy_policy_read:
            raise ValidationError(_("Die Datenschutzerklärung muss akzeptiert sein."))
        if not cancellation_policy_read:
            raise ValidationError(_("Die Widerrufsbelehrung muss akzeptiert sein."))
        policy_text = get_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_CONTRACT_POLICY_CHECKBOX_TEXT, cache=cache
        )
        if policy_text.strip() and not contract_accepted:
            raise ValidationError(_("Vertragsgrundsätze müssen akzeptiert sein."))
        if sepa_allowed and not (iban or member.iban):
            raise ValidationError(_("Für die SEPA-Zustimmung wird eine IBAN benötigt."))

    @classmethod
    def _apply_member_consents(
        cls,
        member: Member,
        sepa_allowed: bool,
        account_owner: str | None,
        iban: str | None,
        payment_rhythm: str | None,
        privacy_policy_read: bool,
        cancellation_policy_read: bool,
        bidding_round: BiddingRound,
        cache: dict,
    ) -> None:
        now = get_now(cache=cache)
        update_fields = []
        if sepa_allowed:
            if account_owner:
                member.account_owner = account_owner
                update_fields.append("account_owner")
            if iban:
                member.iban = iban
                update_fields.append("iban")
            member.sepa_consent = now
            update_fields.append("sepa_consent")
        if privacy_policy_read:
            member.privacy_consent = now
            update_fields.append("privacy_consent")
        if cancellation_policy_read:
            member.withdrawal_consent = now
            update_fields.append("withdrawal_consent")
        if update_fields:
            member.save(update_fields=update_fields)

        if payment_rhythm:
            if not MemberPaymentRhythmService.is_payment_rhythm_allowed(
                rhythm=payment_rhythm, cache=cache
            ):
                raise ValidationError(_("Ungültiger Zahlungsrhythmus."))
            MemberPaymentRhythmService.assign_payment_rhythm_to_member(
                member=member,
                rhythm=payment_rhythm,
                valid_from=bidding_round.growing_period.start_date,
                cache=cache,
                actor=None,
            )
