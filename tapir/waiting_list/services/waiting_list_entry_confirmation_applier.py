import datetime

from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.bestell_wizard.services.bestell_wizard_order_fulfiller import (
    BestellWizardOrderFulfiller,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.waiting_list.models import WaitingListChangeConfirmedLogEntry
from tapir.wirgarten.models import WaitingListEntry, Member
from tapir.wirgarten.service.delivery import calculate_pickup_location_change_date
from tapir.wirgarten.utils import get_now, get_today


class WaitingListEntryConfirmationApplier:
    @classmethod
    @transaction.atomic
    def apply_changes(
        cls,
        waiting_list_entry: WaitingListEntry,
        validated_data: dict,
        request,
        cache: dict,
    ):
        is_new_member = waiting_list_entry.member is None

        member = waiting_list_entry.member
        if is_new_member:
            member = cls.create_member(
                waiting_list_entry=waiting_list_entry,
                validated_data=validated_data,
                cache=cache,
            )

        actor = request.user if request.user.is_authenticated else member
        WaitingListChangeConfirmedLogEntry().populate(actor=actor, user=member).save()

        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=validated_data["payment_rhythm"],
            valid_from=get_today(cache=cache),
            cache=cache,
            actor=actor,
        )

        reference_date = waiting_list_entry.desired_start_date
        if reference_date is None:
            reference_date = get_today(cache=cache)

        contract_start_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=reference_date,
            apply_buffer_time=False,
            cache=cache,
        )

        cls.apply_pickup_location_changes(
            waiting_list_entry=waiting_list_entry,
            contract_start_date=contract_start_date,
            reference_date=reference_date,
            actor=actor,
            member=member,
            cache=cache,
        )

        if not waiting_list_entry.member:
            MemberSolidarityContributionService.assign_contribution_to_member(
                member=member,
                change_date=contract_start_date,
                actor=actor,
                cache=cache,
                amount=validated_data["solidarity_contribution"],
            )

        subscriptions_existed_before_changes, new_subscriptions = (
            cls.apply_subscription_changes(
                waiting_list_entry=waiting_list_entry,
                contract_start_date=contract_start_date,
                actor=actor,
                member=member,
                cache=cache,
            )
        )

        waiting_list_entry.delete()

        if len(new_subscriptions) > 0:
            ApplyTapirOrderManager.send_order_confirmation_mail(
                member=member,
                subscriptions_existed_before_changes=subscriptions_existed_before_changes,
                new_subscriptions=new_subscriptions,
                cache=cache,
                from_waiting_list=True,
            )

        if is_new_member:
            BestellWizardOrderFulfiller.create_coop_shares(
                member=member,
                number_of_shares=validated_data["number_of_coop_shares"],
                subscriptions=new_subscriptions,
                cache=cache,
                actor=actor,
            )

    @classmethod
    def create_member(
        cls, waiting_list_entry: WaitingListEntry, validated_data: dict, cache: dict
    ):
        now = get_now(cache=cache)
        contracts_signed = dict.fromkeys(
            ["sepa_consent", "withdrawal_consent", "privacy_consent"], now
        )

        return Member.objects.create(
            first_name=waiting_list_entry.first_name,
            last_name=waiting_list_entry.last_name,
            email=waiting_list_entry.email,
            phone_number=waiting_list_entry.phone_number,
            street=waiting_list_entry.street,
            street_2=waiting_list_entry.street_2,
            postcode=waiting_list_entry.postcode,
            city=waiting_list_entry.city,
            country=waiting_list_entry.country,
            account_owner=validated_data["account_owner"],
            iban=validated_data["iban"],
            **contracts_signed,
        )

    @classmethod
    def apply_subscription_changes(
        cls,
        waiting_list_entry: WaitingListEntry,
        contract_start_date: datetime.date,
        actor: TapirUser,
        member: Member,
        cache: dict,
    ):
        order = TapirOrderBuilder.build_tapir_order_from_waiting_list_entry(
            waiting_list_entry
        )
        if len(order) == 0:
            return False, []

        return ApplyTapirOrderManager.apply_order_with_several_product_types(
            member=member,
            order=order,
            contract_start_date=contract_start_date,
            actor=actor,
            needs_admin_confirmation=False,
            cache=cache,
        )

    @classmethod
    def apply_pickup_location_changes(
        cls,
        waiting_list_entry: WaitingListEntry,
        contract_start_date: datetime.date,
        reference_date: datetime.date,
        actor: TapirUser,
        member: Member,
        cache: dict,
    ):
        pickup_location_change_valid_from = contract_start_date
        if not waiting_list_entry.product_wishes.exists():
            pickup_location_change_valid_from = calculate_pickup_location_change_date(
                reference_date=reference_date, cache=cache
            )

        pickup_location_wish = waiting_list_entry.pickup_location_wishes.order_by(
            "priority"
        ).first()
        if pickup_location_wish is None:
            return

        MemberPickupLocationService.link_member_to_pickup_location(
            pickup_location_wish.pickup_location_id,
            member=member,
            valid_from=pickup_location_change_valid_from,
            actor=actor,
            cache=cache,
        )
