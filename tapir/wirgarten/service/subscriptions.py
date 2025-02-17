import datetime

from django.db.models import Subquery, OuterRef, F, Case, When, FloatField

from tapir.wirgarten.models import ProductPrice


def annotate_subscriptions_queryset_with_monthly_payment_including_solidarity(
    queryset, reference_date: datetime.date
):
    queryset = annotate_subscriptions_queryset_with_monthly_payment_without_solidarity(
        queryset, reference_date
    )

    return queryset.annotate(
        monthly_payment=Case(
            When(
                solidarity_price_absolute__isnull=True,
                then=(
                    F("monthly_price_without_solidarity") * (1 + F("solidarity_price"))
                ),
            ),
            When(
                solidarity_price_absolute__isnull=False,
                then=(
                    F("monthly_price_without_solidarity")
                    + F("solidarity_price_absolute")
                ),
            ),
            default=0.0,
            output_field=FloatField(),
        )
    )


def annotate_subscriptions_queryset_with_monthly_payment_without_solidarity(
    queryset, reference_date: datetime.date
):
    queryset = annotate_subscriptions_queryset_with_product_price(
        queryset, reference_date
    )
    return queryset.annotate(
        monthly_price_without_solidarity=F("current_product_price") * F("quantity")
    )


def annotate_subscriptions_queryset_with_product_price(
    queryset, reference_date: datetime.date
):
    return queryset.annotate(
        current_product_price=Subquery(
            ProductPrice.objects.filter(
                product_id=OuterRef("product__id"), valid_from__lte=reference_date
            )
            .order_by("-valid_from")
            .values("price")[:1]
        )
    )
