import datetime

from django.db.models import Subquery, OuterRef

from tapir.wirgarten.models import ProductPrice


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
