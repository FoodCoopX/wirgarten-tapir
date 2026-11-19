import datetime

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.contract_prerequisites_validator import (
    ContractPrerequisitesValidator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, Product, Subscription
from tapir.wirgarten.utils import get_today


class AdminSizeChangeValidator:
    @classmethod
    def validate(
        cls,
        member: Member,
        subscription: Subscription,
        new_product: Product,
        change_date: datetime.date,
        order: TapirOrder,
        desired_pickup_location_id: str | None,
        payment_rhythm: str | None,
        iban: str,
        account_owner: str,
        sepa_mandate_confirmed: bool,
        cache: dict,
    ):
        cls.validate_subscription(
            member=member, subscription=subscription, change_date=change_date
        )
        cls.validate_change_date(change_date=change_date, cache=cache)
        cls.validate_new_product(subscription=subscription, new_product=new_product)
        cls.validate_no_other_cancelled_subscription(
            member=member,
            subscription=subscription,
            change_date=change_date,
            cache=cache,
        )

        pickup_location = ContractPrerequisitesValidator.validate_pickup_location(
            order=order,
            member=member,
            contract_start_date=change_date,
            desired_pickup_location_id=desired_pickup_location_id,
            cache=cache,
        )
        OrderValidator.validate_order_general(
            order=order,
            contract_start_date=change_date,
            cache=cache,
            member=member,
            pickup_location=pickup_location,
        )

        ContractPrerequisitesValidator.validate_banking_data(
            member=member,
            account_owner=account_owner,
            iban=iban,
            payment_rhythm=payment_rhythm,
            cache=cache,
        )
        cls.validate_sepa_mandate(
            iban=iban, sepa_mandate_confirmed=sepa_mandate_confirmed
        )

    @classmethod
    def validate_subscription(
        cls, member: Member, subscription: Subscription, change_date: datetime.date
    ):
        if subscription.member.id != member.id:
            raise ValidationError("Dieser Vertrag gehört nicht zu diesem Mitglied.")

        if subscription.cancellation_ts is not None:
            raise ValidationError(
                "Dieser Vertrag ist bereits gekündigt und kann daher nicht bearbeitet werden."
            )

        if not subscription.start_date <= change_date <= subscription.end_date:
            raise ValidationError(
                "Das Datum der Änderung muss innerhalb der Laufzeit des Vertrags liegen."
            )

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
        for other_subscription in TapirCache.get_all_subscriptions_for_member(
            member_id=member.id, cache=cache
        ):
            if (
                other_subscription.id != subscription.id
                and other_subscription.product.type_id == subscription.product.type_id
                and other_subscription.start_date
                <= change_date
                <= other_subscription.end_date
                and other_subscription.cancellation_ts is not None
            ):
                raise ValidationError(
                    f"Der Vertrag {other_subscription.long_str()} derselben Vertragsart ist gekündigt. "
                    f"Eine Änderung würde die Kündigung aufheben."
                )

    @classmethod
    def validate_sepa_mandate(cls, iban: str, sepa_mandate_confirmed: bool):
        if iban.strip() != "" and not sepa_mandate_confirmed:
            raise ValidationError(
                "Bitte bestätige, dass ein unterschriebenes SEPA-Mandat vorliegt."
            )
