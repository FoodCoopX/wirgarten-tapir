import datetime

from tapir.accounts.models import TapirUser
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_delivery_address_setter import (
    MemberDeliveryAddressSetter,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today, get_now


class SubscriptionPrerequisitesApplier:
    @classmethod
    def apply_delivery_address_and_pickup_location(
        cls,
        member: Member,
        subscription_start_date: datetime.date,
        desired_pickup_location_id: str,
        actor: TapirUser,
        cache: dict,
    ):
        MemberDeliveryAddressSetter.save_delivery_address(member=member, actor=actor)

        if (
            desired_pickup_location_id
            != MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=subscription_start_date
            )
        ):
            MemberPickupLocationSetter.link_member_to_pickup_location(
                member=member,
                valid_from=subscription_start_date,
                pickup_location_id=desired_pickup_location_id,
                actor=actor,
                cache=cache,
            )

    @classmethod
    def change_payment_rhythm_if_necessary(
        cls, payment_rhythm: str | None, member: Member, actor: TapirUser, cache: dict
    ):
        if payment_rhythm is None:
            return

        rhythm_valid_from = (
            MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
                member=member,
                reference_date=get_today(cache=cache),
                cache=cache,
            )
        )
        if (
            MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=rhythm_valid_from, cache=cache
            )
            == payment_rhythm
        ):
            return

        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            actor=actor,
            rhythm=payment_rhythm,
            valid_from=rhythm_valid_from,
            cache=cache,
        )

    @classmethod
    def apply_banking_data(
        cls,
        member: Member,
        iban: str,
        account_owner: str,
        sepa_consent_given: bool,
        cache: dict,
    ):
        if iban.strip() != "":
            member.iban = iban

        if account_owner.strip() != "":
            member.account_owner = account_owner

        if sepa_consent_given:
            member.sepa_consent = get_now(cache=cache)

        member.save()
