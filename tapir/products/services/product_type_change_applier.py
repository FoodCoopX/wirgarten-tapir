from tapir.bestell_wizard.models import ProductTypeAccordionInBestellWizard
from tapir.deliveries.models import CustomCycleDeliveryWeeks
from tapir.products.services.product_type_change_validator import (
    ProductTypeChangeValidator,
)
from tapir.products.services.tax_rate_service import TaxRateService
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.wirgarten.models import ProductType, ProductCapacity


class ProductTypeChangeApplier:
    direct_fields = [
        "name",
        "description_bestellwizard_short",
        "description_bestellwizard_long",
        "order_in_bestellwizard",
        "icon_link",
        "contract_link",
        "delivery_cycle",
        "single_subscription_only",
        "is_affected_by_jokers",
        "must_be_subscribed_to",
        "is_association_membership",
        "force_waiting_list",
        "title_bestellwizard_product_choice",
        "title_bestellwizard_intro",
        "background_image_in_bestellwizard",
    ]

    @classmethod
    def apply_changes(
        cls,
        product_type: ProductType,
        extended_data: dict,
        product_capacity: ProductCapacity,
    ):
        for field in cls.direct_fields:
            setattr(product_type, field, extended_data[field])

        product_type.save()

        product_capacity.capacity = extended_data["capacity"]
        product_capacity.save()

        NoticePeriodManager.set_notice_period_duration(
            product_type=product_capacity.product_type,
            growing_period=product_capacity.period,
            notice_period_duration=extended_data.get("notice_period_duration", None),
            notice_period_unit=extended_data.get("notice_period_unit", None),
        )

        TaxRateService.create_or_update_default_tax_rate(
            product_type_id=product_type.id,
            tax_rate=extended_data["tax_rate"],
            tax_rate_change_date=extended_data["tax_rate_change_date"],
        )

        cls.apply_bestell_wizard_accordion_changes(
            extended_data=extended_data, product_type=product_type
        )
        cls.apply_custom_cycle_delivery_week_changes(
            extended_data=extended_data, product_type=product_type
        )

    @classmethod
    def apply_custom_cycle_delivery_week_changes(
        cls, extended_data: dict, product_type: ProductType
    ):
        CustomCycleDeliveryWeeks.objects.filter(product_type=product_type).delete()

        CustomCycleDeliveryWeeks.objects.bulk_create(
            ProductTypeChangeValidator.build_week_objects(
                extended_data=extended_data, product_type=product_type
            )
        )

    @classmethod
    def apply_bestell_wizard_accordion_changes(
        cls, extended_data: dict, product_type: ProductType
    ):
        ProductTypeAccordionInBestellWizard.objects.filter(
            product_type=product_type
        ).delete()
        accordions = [
            ProductTypeAccordionInBestellWizard(
                product_type=product_type,
                title=accordion_data["title"],
                description=accordion_data["description"],
                order=index,
            )
            for index, accordion_data in enumerate(
                extended_data["accordions_in_bestell_wizard"]
            )
        ]
        ProductTypeAccordionInBestellWizard.objects.bulk_create(accordions)
