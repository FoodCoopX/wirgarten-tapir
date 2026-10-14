from apps.commissioning.models import DeliveryStation, ShareType, ShareTypeVariation
from apps.commissioning.models.choices import (
    DeliveryCycleOptions,
    ShareOptions,
)

from tapir.wirgarten.constants import (
    NO_DELIVERY,
    WEEKLY,
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
)
from tapir.wirgarten.models import PickupLocation, ProductType, Product


class JasminSynchronisationException(Exception):
    def __init__(self, message: str, *args):
        self.message = message
        super().__init__(*args)


class JasminSynchronisationService:
    TAPIR_TO_JASMIN_DELIVERY_CYCLE_MAP = {
        WEEKLY[0]: DeliveryCycleOptions.WEEKLY,
        ODD_WEEKS[0]: DeliveryCycleOptions.ODD_WEEKS,
        EVEN_WEEKS[0]: DeliveryCycleOptions.EVEN_WEEKS,
        EVERY_FOUR_WEEKS[0]: DeliveryCycleOptions.ALL_FOUR_WEEKS,
    }

    KEYWORD_TO_JASMIN_SHARE_OPTION_MAP = {
        "ernte": ShareOptions.HARVEST_SHARE,
        "obst": ShareOptions.HARVEST_SHARE_FRUITS_ONLY,
        "hühn": ShareOptions.CHICKEN_SHARE,
        "eier": ShareOptions.CHICKEN_SHARE,
    }

    @classmethod
    def synchronise_everything(cls):
        cls.synchronise_pickup_locations()
        cls.synchronise_product_types()
        cls.synchronise_products()

    @classmethod
    def synchronise_pickup_locations(cls):
        tapir_names = set(PickupLocation.objects.values_list("name", flat=True))
        jasmin_names = set(DeliveryStation.objects.values_list("short_name", flat=True))

        locations_names_to_delete = jasmin_names.difference(tapir_names)
        if len(locations_names_to_delete) > 0:
            DeliveryStation.objects.filter(
                short_name__in=locations_names_to_delete
            ).delete()

        location_names_to_create = tapir_names.difference(jasmin_names)
        if len(location_names_to_create) > 0:
            DeliveryStation.objects.bulk_create(
                [DeliveryStation(short_name=name) for name in location_names_to_create]
            )

    @classmethod
    def synchronise_product_types(cls):
        tapir_product_types_by_name = {
            product_type.name: product_type
            for product_type in ProductType.objects.exclude(
                delivery_cycle=NO_DELIVERY[0]
            )
        }
        jasmin_product_types_by_name = {
            product_type.name: product_type for product_type in ShareType.objects.all()
        }

        tapir_names = set(tapir_product_types_by_name.keys())
        jasmin_names = set(jasmin_product_types_by_name.keys())

        names_to_delete = jasmin_names.difference(tapir_names)
        if len(names_to_delete) > 0:
            ShareType.objects.filter(name__in=names_to_delete)

        names_to_create = tapir_names.difference(jasmin_names)
        if len(names_to_create) > 0:
            jasmin_product_types_to_create = []
            for name in names_to_create:
                tapir_product_type = tapir_product_types_by_name[name]
                jasmin_product_types_to_create.append(
                    cls.build_jasmin_product_type(tapir_product_type)
                )

            ShareType.objects.bulk_create(jasmin_product_types_to_create)

    @classmethod
    def build_jasmin_product_type(cls, tapir_product_type: ProductType) -> ShareType:
        return ShareType(
            name=tapir_product_type.name,
            short_name=tapir_product_type.name,
            delivery_cycle=cls.get_jasmin_delivery_cycle(
                tapir_product_type.delivery_cycle
            ),
            valid_from=tapir_product_type.created_at.date(),
            share_option=cls.get_jasmin_share_option(tapir_product_type.name),
        )

    @classmethod
    def get_jasmin_delivery_cycle(cls, tapir_delivery_cycle: str):
        if tapir_delivery_cycle not in cls.TAPIR_TO_JASMIN_DELIVERY_CYCLE_MAP:
            raise JasminSynchronisationException(
                f"Folgende Lieferzyklus wird von Jasmin nicht unterstützt: {tapir_delivery_cycle}"
            )

        return cls.TAPIR_TO_JASMIN_DELIVERY_CYCLE_MAP[tapir_delivery_cycle]

    @classmethod
    def get_jasmin_share_option(cls, product_type_name: str):
        for keyword, share_option in cls.KEYWORD_TO_JASMIN_SHARE_OPTION_MAP.items():
            if keyword.casefold() in product_type_name.casefold():
                return share_option

        # Harvest share as default so that the share type is shown on the frontend
        return ShareOptions.HARVEST_SHARE

    @classmethod
    def synchronise_products(cls):
        tapir_product_by_name = {
            product.name: product
            for product in Product.objects.select_related("type").exclude(
                type__delivery_cycle=NO_DELIVERY[0]
            )
        }
        jasmin_product_by_name = {
            product.description: product for product in ShareTypeVariation.objects.all()
        }

        tapir_names = set(tapir_product_by_name.keys())
        jasmin_names = set(jasmin_product_by_name.keys())

        names_to_delete = jasmin_names.difference(tapir_names)
        if len(names_to_delete) > 0:
            ShareTypeVariation.objects.filter(description__in=names_to_delete)

        names_to_create = tapir_names.difference(jasmin_names)
        if len(names_to_create) > 0:
            jasmin_product_to_create = []
            for name in names_to_create:
                tapir_product = tapir_product_by_name[name]
                jasmin_product_to_create.append(cls.build_jasmin_product(tapir_product))

            ShareTypeVariation.objects.bulk_create(jasmin_product_to_create)

    @classmethod
    def build_jasmin_product(cls, tapir_product: Product):
        return ShareTypeVariation(
            share_type=ShareType.objects.get(name=tapir_product.type.name),
            variation_type=ShareTypeVariation.VariationType.PHYSICAL,
            size=tapir_product.name,
            valid_from=tapir_product.created_at.date(),
            description=tapir_product.name,
        )
