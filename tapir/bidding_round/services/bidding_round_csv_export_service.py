import csv
from io import StringIO

from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)


class BiddingRoundCsvExportService:
    @classmethod
    def build_csv(cls, bidding_round, cache: dict) -> str:
        buffer = StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(
            [
                _("Mitglied"),
                _("E-Mail"),
                _("Produkttyp"),
                _("Produkt"),
                _("Anteile"),
                _("Betrag (effektive Stufe)"),
                _("Betrag / Monat"),
                _("Betrag / Jahr"),
                _("Bestätigt"),
                _("Abholort"),
            ]
        )
        position = BiddingRoundStatsService.get_default_position(
            bidding_round, cache=cache
        )
        for bid in bidding_round.bids.select_related("member", "product"):
            pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
                member=bid.member,
                reference_date=bidding_round.growing_period.start_date,
                cache=cache,
            )
            monthly_amount = BiddingRoundStatsService.get_bid_monthly_amount(
                bid, position, bidding_round
            )
            writer.writerow(
                [
                    cls._sanitize_cell(str(bid.member)),
                    cls._sanitize_cell(bid.member.email),
                    cls._sanitize_cell(bid.product.type.name),
                    cls._sanitize_cell(bid.product.name),
                    bid.quantity,
                    BiddingRoundStatsService.get_effective_amount(
                        bid, position, bidding_round
                    ),
                    monthly_amount,
                    monthly_amount * 12,
                    "ja" if bid.admin_confirmed else "nein",
                    cls._sanitize_cell(pickup_location.name if pickup_location else ""),
                ]
            )
        return buffer.getvalue()

    @staticmethod
    def _sanitize_cell(value) -> str:
        text = "" if value is None else str(value)
        if text and text[0] in ("=", "+", "-", "@"):
            return "'" + text
        return text
