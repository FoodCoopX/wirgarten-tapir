import datetime

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_start_date_validator import (
    AdminStartDateValidator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.subscription_prerequisites_validator import (
    SubscriptionPrerequisitesValidator,
)
from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.subscriptions.types import AdminSubscriptionAddition
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, Product


class AdminSubscriptionAdditionValidator:
    @classmethod
    def validate(cls, addition: AdminSubscriptionAddition, cache: dict):
        cls.validate_product_and_quantity(
            product=addition.product, quantity=addition.quantity
        )
        cls.validate_no_subscription_of_same_product(
            member=addition.member,
            product=addition.product,
            start_date=addition.start_date,
            cache=cache,
        )
        AdminStartDateValidator.validate_start_date(
            start_date=addition.start_date, cache=cache
        )
        cls.validate_start_date_not_after_last_period(
            start_date=addition.start_date, cache=cache
        )
        SubscriptionUpdateViewValidator.validate_optional_product_can_be_ordered_without_required_product_subscription(
            product_type=addition.product.type,
            member=addition.member,
            contract_start_date=addition.start_date,
            cache=cache,
        )

        order = {addition.product: addition.quantity}
        pickup_location = SubscriptionPrerequisitesValidator.validate_pickup_location(
            order=order,
            member=addition.member,
            subscription_start_date=addition.start_date,
            desired_pickup_location_id=addition.prerequisites.desired_pickup_location_id,
            cache=cache,
        )
        # With member=None, the capacity checks count the order on top of all existing subscriptions,
        # instead of as a replacement of the member's current ones.
        OrderValidator.validate_order_general(
            order=order,
            contract_start_date=addition.start_date,
            cache=cache,
            member=None,
            pickup_location=pickup_location,
        )

        SubscriptionPrerequisitesValidator.validate_banking_data(
            member=addition.member,
            account_owner=addition.prerequisites.account_owner,
            iban=addition.prerequisites.iban,
        )
        SubscriptionPrerequisitesValidator.validate_sepa_mandate(
            iban=addition.prerequisites.iban,
            sepa_mandate_confirmed=addition.prerequisites.sepa_mandate_confirmed,
        )

    @classmethod
    def validate_product_and_quantity(cls, product: Product, quantity: int):
        if quantity < 1:
            raise ValidationError("Die Anzahl der Anteile muss mindestens 1 sein.")

        if product.deleted:
            raise ValidationError("Diese Produktanteilsgröße ist nicht mehr verfügbar.")

    @classmethod
    def validate_no_subscription_of_same_product(
        cls, member: Member, product: Product, start_date: datetime.date, cache: dict
    ):
        for subscription in TapirCache.get_all_subscriptions_for_member(
            member_id=member.id, cache=cache
        ):
            if (
                subscription.product_id == product.id
                and subscription.end_date >= start_date
            ):
                raise ValidationError(
                    f"Dieses Mitglied hat bereits einen Vertrag für {product.name} ab diesem Datum. "
                    f"Um die Anzahl der Anteile zu ändern, wende dich bitte an die FoodCoopX-Admins."
                )

    @classmethod
    def validate_start_date_not_after_last_period(
        cls, start_date: datetime.date, cache: dict
    ):
        last_date = cls.get_last_possible_start_date(cache=cache)
        if last_date is None or start_date > last_date:
            raise ValidationError(
                "Der Vertragsbeginn muss in einer bestehenden Vertragsperiode liegen."
            )

    @classmethod
    def get_last_possible_start_date(cls, cache: dict) -> datetime.date | None:
        growing_periods = TapirCache.get_all_growing_periods_ascending(cache=cache)
        if len(growing_periods) == 0:
            return None
        return growing_periods[-1].end_date
