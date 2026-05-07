import datetime

from tapir.accounts.models import TapirUser
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import Member, ProductType
from tapir.wirgarten.utils import get_today, get_now


class SubscriptionUpdateViewChangeApplier:
    @classmethod
    def apply_changes(
        cls,
        member: Member,
        product_type: ProductType,
        contract_start_date: datetime.date,
        actor: TapirUser,
        desired_pickup_location_id: str,
        order: TapirOrder,
        payment_rhythm: str | None,
        iban: str,
        account_owner: str,
        sepa_allowed: bool,
        cache: dict,
    ):
        if (
            desired_pickup_location_id
            != MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=contract_start_date
            )
        ):
            MemberPickupLocationSetter.link_member_to_pickup_location(
                member=member,
                valid_from=contract_start_date,
                pickup_location_id=desired_pickup_location_id,
                actor=actor,
                cache=cache,
            )

        cls.change_payment_rhythm_if_necessary(
            payment_rhythm=payment_rhythm, member=member, actor=actor, cache=cache
        )

        subscriptions_existed_before_changes, new_subscriptions = (
            ApplyTapirOrderManager.apply_order_single_product_type(
                member=member,
                order=order,
                contract_start_date=contract_start_date,
                product_type=product_type,
                actor=actor,
                needs_admin_confirmation=True,
                cache=cache,
            )
        )

        ApplyTapirOrderManager.send_order_confirmation_mail(
            subscriptions_existed_before_changes=subscriptions_existed_before_changes,
            member=member,
            new_subscriptions=new_subscriptions,
            cache=cache,
            from_waiting_list=False,
            solidarity_contribution=None,
        )

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            actor=actor,
            product_type_id_or_soli=product_type.id,
            reference_date=contract_start_date,
            comment="Produkt-Anteil vom Admin durch dem Mitgliederbereich reduziert",
            cache=cache,
        )

        if iban.strip() != "":
            member.iban = iban

        if account_owner.strip() != "":
            member.account_owner = account_owner

        if sepa_allowed:
            member.sepa_consent = get_now(cache=cache)

        member.save()

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
