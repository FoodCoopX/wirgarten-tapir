from collections import Counter

from tapir_mail.models import StaticSegmentRecipient

from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.user_utils import UserUtils
from tapir.wirgarten.models import Member, Product
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.utils import get_today


class MemberMailTokenService:
    @classmethod
    def get_post_address(cls, recipient: Member | StaticSegmentRecipient, cache: dict):
        if not isinstance(recipient, Member):
            return ""

        return UserUtils.build_display_address(
            street=recipient.street,
            street_2=recipient.street_2,
            postcode=recipient.postcode,
            city=recipient.city,
        )

    @classmethod
    def get_base_subscriptions_text(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        if not isinstance(recipient, Member):
            return ""

        today = get_today(cache=cache)
        quantity_by_product = Counter()
        for subscription in TapirCache.get_all_subscriptions_for_member(
            member_id=recipient.id, cache=cache
        ):
            if (
                subscription.product.type.must_be_subscribed_to
                and subscription.start_date <= today <= subscription.end_date
            ):
                quantity_by_product[subscription.product] += subscription.quantity

        products = sorted(
            quantity_by_product,
            key=lambda product: get_product_price(
                product=product, reference_date=today, cache=cache
            ).price,
        )
        return " + ".join(
            cls._format_product_quantity(
                product=product, quantity=quantity_by_product[product]
            )
            for product in products
        )

    @staticmethod
    def _format_product_quantity(product: Product, quantity: int) -> str:
        if quantity == 1:
            return f"einen {product.name}-{product.type.name[:-1]}"
        return f"{quantity} {product.name}-{product.type.name}"
