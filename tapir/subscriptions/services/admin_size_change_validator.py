import datetime

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_size_change_next_period_finder import (
    AdminSizeChangeNextPeriodFinder,
)
from tapir.subscriptions.services.subscription_prerequisites_validator import (
    SubscriptionPrerequisitesValidator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.types import AdminSizeChangeRequest, TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, PickupLocation, Product, Subscription
from tapir.wirgarten.utils import get_today


class AdminSizeChangeValidator:
    @classmethod
    def validate(cls, size_change: AdminSizeChangeRequest, cache: dict):
        cls.validate_subscription(
            member=size_change.member,
            subscription=size_change.subscription,
            change_date=size_change.change_date,
            cache=cache,
        )
        cls.validate_change_date(change_date=size_change.change_date, cache=cache)
        cls.validate_new_product(
            subscription=size_change.subscription,
            new_product=size_change.new_product,
        )
        cls.validate_no_other_cancelled_subscription(
            member=size_change.member,
            subscription=size_change.subscription,
            change_date=size_change.change_date,
            cache=cache,
        )

        pickup_location = SubscriptionPrerequisitesValidator.validate_pickup_location(
            order=size_change.order,
            member=size_change.member,
            subscription_start_date=size_change.change_date,
            desired_pickup_location_id=size_change.prerequisites.desired_pickup_location_id,
            cache=cache,
        )
        OrderValidator.validate_order_general(
            order=size_change.order,
            contract_start_date=size_change.change_date,
            cache=cache,
            member=size_change.member,
            pickup_location=pickup_location,
        )
        cls.validate_next_period_capacity(
            member=size_change.member,
            subscription=size_change.subscription,
            change_date=size_change.change_date,
            order=size_change.order,
            pickup_location=pickup_location,
            cache=cache,
        )

        SubscriptionPrerequisitesValidator.validate_banking_data(
            member=size_change.member,
            account_owner=size_change.prerequisites.account_owner,
            iban=size_change.prerequisites.iban,
        )
        cls.validate_sepa_mandate(
            iban=size_change.prerequisites.iban,
            sepa_mandate_confirmed=size_change.prerequisites.sepa_mandate_confirmed,
        )

    @classmethod
    def validate_subscription(
        cls,
        member: Member,
        subscription: Subscription,
        change_date: datetime.date,
        cache: dict,
    ):
        if subscription.member.id != member.id:
            raise ValidationError("Dieser Vertrag gehört nicht zu diesem Mitglied.")

        if subscription.cancellation_ts is not None:
            raise ValidationError(
                "Dieser Vertrag ist bereits gekündigt und kann daher nicht bearbeitet werden."
            )

        if subscription.start_date <= change_date <= subscription.end_date:
            return

        if cls.is_change_from_next_period(
            subscription=subscription, change_date=change_date, cache=cache
        ):
            return

        raise ValidationError(
            "Das Datum der Änderung muss innerhalb der Laufzeit des Vertrags oder am Beginn der folgenden Vertragsperiode liegen."
        )

    @classmethod
    def is_change_from_next_period(
        cls, subscription: Subscription, change_date: datetime.date, cache: dict
    ) -> bool:
        if change_date != subscription.end_date + datetime.timedelta(days=1):
            return False

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=change_date, cache=cache
        )
        return growing_period is not None and growing_period.start_date == change_date

    @classmethod
    def validate_change_date(cls, change_date: datetime.date, cache: dict):
        if change_date < get_today(cache=cache):
            raise ValidationError(
                "Das Datum der Änderung darf nicht in der Vergangenheit liegen."
            )

        if change_date.weekday() == 0:
            return

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=change_date, cache=cache
        )
        if growing_period is None or growing_period.start_date != change_date:
            raise ValidationError(
                "Das Datum der Änderung muss ein Montag oder der Beginn einer Vertragsperiode sein."
            )

    @classmethod
    def validate_new_product(cls, subscription: Subscription, new_product: Product):
        if new_product.type_id != subscription.product.type_id:
            raise ValidationError(
                "Die neue Produktanteilsgröße muss zur gleichen Vertragsart gehören."
            )

        if new_product.deleted:
            raise ValidationError("Diese Produktanteilsgröße ist nicht mehr verfügbar.")

        if new_product.id == subscription.product_id:
            raise ValidationError(
                "Die neue Produktanteilsgröße muss sich von der bisherigen unterscheiden."
            )

    @classmethod
    def validate_no_other_cancelled_subscription(
        cls,
        member: Member,
        subscription: Subscription,
        change_date: datetime.date,
        cache: dict,
    ):
        base_date = min(change_date, subscription.end_date)
        for other_subscription in TapirCache.get_all_subscriptions_for_member(
            member_id=member.id, cache=cache
        ):
            if (
                other_subscription.id != subscription.id
                and other_subscription.product.type_id == subscription.product.type_id
                and other_subscription.start_date
                <= base_date
                <= other_subscription.end_date
                and other_subscription.cancellation_ts is not None
            ):
                raise ValidationError(
                    f"Der Vertrag {other_subscription.long_str()} derselben Vertragsart ist gekündigt. "
                    f"Eine Änderung würde die Kündigung aufheben."
                )

    @classmethod
    def validate_next_period_capacity(
        cls,
        member: Member,
        subscription: Subscription,
        change_date: datetime.date,
        order: TapirOrder,
        pickup_location: PickupLocation | None,
        cache: dict,
    ):
        if change_date > subscription.end_date:
            return

        next_growing_period = (
            AdminSizeChangeNextPeriodFinder.get_next_period_with_subscriptions(
                member=member, subscription=subscription, cache=cache
            )
        )
        if next_growing_period is None:
            return

        OrderValidator.validate_capacities(
            order=order,
            subscription_start_date=next_growing_period.start_date,
            member=member,
            pickup_location=pickup_location,
            cache=cache,
        )

    @classmethod
    def validate_sepa_mandate(cls, iban: str, sepa_mandate_confirmed: bool):
        if iban.strip() != "" and not sepa_mandate_confirmed:
            raise ValidationError(
                "Bitte bestätige, dass ein unterschriebenes SEPA-Mandat vorliegt."
            )
