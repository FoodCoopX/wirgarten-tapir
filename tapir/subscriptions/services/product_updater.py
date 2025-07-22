from decimal import Decimal

from django.db import transaction

from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.subscriptions.serializers import ExtendedProductSerializer
from tapir.wirgarten.models import Product
from tapir.wirgarten.service.products import update_product


class ProductUpdater:
    @classmethod
    @transaction.atomic
    def update_product(cls, product: Product, serializer: ExtendedProductSerializer):
        update_product(
            id_=product.id,
            name=serializer.validated_data["name"],
            base=serializer.validated_data["base"],
            price=Decimal(serializer.validated_data["price"]),
            size=Decimal(serializer.validated_data["size"]),
            growing_period_id=serializer.validated_data["growing_period_id"],
            description_in_bestellwizard=serializer.validated_data[
                "description_in_bestellwizard"
            ],
            url_of_image_in_bestellwizard=serializer.validated_data[
                "url_of_image_in_bestellwizard"
            ],
            capacity=serializer.validated_data.get("capacity", None),
        )

        ProductBasketSizeEquivalence.objects.filter(product=product).delete()

        ProductBasketSizeEquivalence.objects.bulk_create(
            [
                ProductBasketSizeEquivalence(
                    product=product,
                    basket_size_name=equivalence["basket_size_name"],
                    quantity=equivalence["quantity"],
                )
                for equivalence in serializer.validated_data["basket_size_equivalences"]
            ]
        )
