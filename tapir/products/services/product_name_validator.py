from django.core.exceptions import ValidationError

from tapir.utils.services.tapir_cache import TapirCache


class ProductNameValidator:
    @classmethod
    def validate_name_is_unique(
        cls, product_name: str, product_id: str | None, cache: dict
    ) -> None:
        for product in TapirCache.get_all_products(cache=cache):
            if product.deleted or product.id == product_id:
                continue
            if product.name == product_name:
                raise ValidationError(
                    f"Es gibt bereits ein Produkt mit dem Namen „{product_name}“."
                )
