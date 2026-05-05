import datetime
from decimal import Decimal

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Subquery, OuterRef, F, QuerySet, Case, When, DecimalField

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

        price_object = get_product_price(
            product=subscription.product, reference_date=reference_date, cache=cache
        )
        if price_object is None:
            raise ImproperlyConfigured(
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
        return queryset.annotate(
            **{
                cls.ANNOTATION_MONTHLY_PRICE: Case(
                    When(
                        price_override__isnull=True,
                        then=F(cls.ANNOTATION_CURRENT_PRODUCT_PRICE) * F("quantity"),
                    ),
                    default=F("price_override"),
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
