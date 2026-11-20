import datetime

from django.core.exceptions import ValidationError
from localflavor.generic.validators import IBANValidator

from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.home_delivery_address_validator import (
    HomeDeliveryAddressValidator,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, PickupLocation
from tapir.wirgarten.utils import get_today


class SubscriptionPrerequisitesValidator:
    @classmethod
    def validate_banking_data(
        cls,
        member: Member,
        account_owner: str,
        iban: str,
    ):
        if MemberNeedsBankingDataChecker.does_member_need_banking_data(member):
            IBANValidator()(iban)

            if account_owner == "":
                raise ValidationError("Das Feld 'Kontoinhaber*in' muss ausgefüllt sein")

    @classmethod
    def validate_payment_rhythm(
        cls, member: Member, payment_rhythm: str | None, cache: dict
    ):
        need_payment_rhythm = (
            TapirCache.get_member_payment_rhythm_object(
                member=member,
                reference_date=get_today(cache=cache),
                cache=cache,
            )
            is None
        )

        if need_payment_rhythm and payment_rhythm is None:
            raise ValidationError("Das Zahlungsintervall fehlt")

        if payment_rhythm is None:
            return

        if not MemberPaymentRhythmService.is_payment_rhythm_allowed(
            payment_rhythm, cache=cache
        ):
            raise ValidationError(
                f"Dieses Zahlungsintervall {payment_rhythm} ist nicht erlaubt, erlaubt sind: {MemberPaymentRhythmService.get_allowed_rhythms(cache=cache)}"
            )

    @classmethod
    def validate_pickup_location(
        cls,
        order: TapirOrder,
        member: Member,
        subscription_start_date: datetime.date,
        desired_pickup_location_id: str | None,
        cache: dict,
    ):
        if not OrderValidator.does_order_need_a_pickup_location(
            order=order, cache=cache
        ):
            return None

        current_pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=subscription_start_date
            )
        )
        if (
            current_pickup_location_id is not None
            and desired_pickup_location_id is not None
            and current_pickup_location_id != desired_pickup_location_id
        ):
            raise ValidationError("Du hast schon eine Verteilstation")

        pickup_location_id = current_pickup_location_id or desired_pickup_location_id
        if pickup_location_id is None:
            raise ValidationError("Bitte wähle einen Abholort aus!")

        pickup_location = PickupLocation.objects.get(id=pickup_location_id)
        if current_pickup_location_id is None:
            HomeDeliveryAddressValidator.validate(
                address_owner=member, pickup_location=pickup_location
            )

        return pickup_location

    @classmethod
    def validate_sepa_mandate(cls, iban: str, sepa_mandate_confirmed: bool):
        if iban.strip() != "" and not sepa_mandate_confirmed:
            raise ValidationError(
                "Bitte bestätige, dass ein unterschriebenes SEPA-Mandat vorliegt."
            )
