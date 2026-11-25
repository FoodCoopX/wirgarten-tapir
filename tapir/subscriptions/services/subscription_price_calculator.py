import datetime
from decimal import Decimal

from django.db.models import Subquery, OuterRef, F, QuerySet, Case, When, DecimalField

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.subscriptions.services.subscription_price_provider import (
    SubscriptionPriceProvider,
)
from tapir.wirgarten.models import Subscription, ProductPrice
from tapir.wirgarten.service.products import get_product_price


class SubscriptionPriceCalculator:
    ANNOTATION_CURRENT_PRODUCT_PRICE = "current_product_price"
    ANNOTATION_MONTHLY_PRICE = "monthly_price"

    @classmethod
    def get_monthly_price(
        cls, subscription: Subscription, reference_date: datetime.date, cache: dict
    ) -> Decimal:
        if subscription.price_override is not None:
            return subscription.price_override

        provider_price = SubscriptionPriceProvider.get_price(subscription, cache)
        if provider_price is not None:
            return provider_price

        price_object = get_product_price(
            product=subscription.product, reference_date=reference_date, cache=cache
        )
        if price_object is None:
            raise TapirImproperlyConfigured(
                f"Can't find price for product {subscription.product} at {reference_date}"
            )
        return subscription.quantity * price_object.price

    @classmethod
    def annotate_subscriptions_queryset_with_monthly_price(
        cls, queryset: QuerySet[Subscription], reference_date: datetime.date
    ):
        queryset = cls.annotate_subscriptions_queryset_with_product_price(
            queryset, reference_date
        )
        queryset = SubscriptionPriceProvider.apply_annotations(queryset)
        return queryset.annotate(
            **{
                cls.ANNOTATION_MONTHLY_PRICE: Case(
                    When(price_override__isnull=False, then=F("price_override")),
                    *SubscriptionPriceProvider.get_price_whens(),
                    default=F(cls.ANNOTATION_CURRENT_PRODUCT_PRICE) * F("quantity"),
                    output_field=DecimalField(),
                )
            }
        )

    @classmethod
    def annotate_subscriptions_queryset_with_product_price(
        cls, queryset: QuerySet[Subscription], reference_date: datetime.date
    ):
        return queryset.annotate(
            **{
                cls.ANNOTATION_CURRENT_PRODUCT_PRICE: Subquery(
                    ProductPrice.objects.filter(
                        product_id=OuterRef("product__id"),
                        valid_from__lte=reference_date,
                    )
                    .order_by("-valid_from")
                    .values("price")[:1]
                )
            }
        )
