from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.models import BiddingRound
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.wirgarten.models import Product, ProductPrice
from tapir.wirgarten.service.products import (
    get_next_product_price_change_date,
    get_product_price,
)
from tapir.wirgarten.utils import get_today


class BiddingRoundStandardPriceService:
    @classmethod
    def align_standard_prices(
        cls, bidding_round: BiddingRound, cache: dict
    ) -> list[dict]:
        period = bidding_round.growing_period
        if period.end_date < get_today(cache=cache):
            raise ValidationError(_("Die Vertragsperiode ist bereits beendet."))
        if (
            bidding_round.average_bid_locked_at is None
            or bidding_round.locked_bidder_average_per_share_per_month is None
        ):
            raise ValidationError(_("Das Durchschnittsgebot muss gesperrt sein."))

        target = bidding_round.locked_bidder_average_per_share_per_month.quantize(
            Decimal("0.01")
        )
        if target <= 0:
            raise ValidationError(
                _("Der gesperrte Durchschnittspreis muss größer als 0 sein.")
            )

        valid_from = get_next_product_price_change_date(period.id)
        products = Product.objects.filter(
            type_id=bidding_round.product_type_id,
            deleted=False,
        ).order_by("name")

        results = []
        with transaction.atomic():
            for product in products:
                round_size = BiddingRoundStatsService.get_product_size(
                    product, bidding_round, cache
                )
                price = (target * round_size).quantize(Decimal("0.01"))
                ProductPrice.objects.update_or_create(
                    product=product,
                    valid_from=valid_from,
                    defaults={
                        "price": price,
                        "size": cls._get_size(product, period, cache),
                    },
                )
                results.append(
                    {
                        "product_id": product.id,
                        "product_name": product.name,
                        "price": str(price),
                        "valid_from": valid_from,
                    }
                )
        return results

    @classmethod
    def _get_size(cls, product: Product, period, cache: dict) -> Decimal:
        product_price = get_product_price(
            product, reference_date=period.start_date, cache=cache
        )
        if product_price is None:
            product_price = (
                ProductPrice.objects.filter(product=product)
                .order_by("-valid_from")
                .first()
            )
        if product_price is not None and product_price.size:
            return product_price.size
        return Decimal("1")
