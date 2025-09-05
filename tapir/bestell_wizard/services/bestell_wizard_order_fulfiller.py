import datetime

from tapir.accounts.models import TapirUser
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import (
    Member,
    Subscription,
)
from tapir.wirgarten.service.member import (
    send_order_confirmation,
)
from tapir.wirgarten.utils import (
    get_today,
    get_now,
    legal_status_is_cooperative,
)


class BestellWizardOrderFulfiller:
    @classmethod
    def create_member_and_fulfill_order(
        cls,
        validated_serializer_data: dict,
        contract_start_date: datetime.date,
        request,
        cache: dict,
    ):
        member = cls.create_member(
            personal_data=validated_serializer_data["personal_data"], cache=cache
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=validated_serializer_data["payment_rhythm"],
            valid_from=get_today(cache=cache),
        )

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            validated_serializer_data["shopping_cart"], cache=cache
        )
        subscriptions = cls.create_subscriptions(
            order=order,
            member=member,
            actor=request.user if request.user.is_authenticated else None,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        if OrderValidator.does_order_need_a_pickup_location(order=order, cache=cache):
            MemberPickupLocationService.link_member_to_pickup_location(
                validated_serializer_data["pickup_location_id"],
                member=member,
                valid_from=contract_start_date,
                actor=request.user if request.user.is_authenticated else member,
                cache=cache,
            )

        if legal_status_is_cooperative(cache=cache):
            cls.create_coop_shares(
                number_of_shares=validated_serializer_data["nb_shares"],
                member=member,
                subscriptions=subscriptions,
                cache=cache,
            )

        send_order_confirmation(
            member, subscriptions, cache=cache, from_waiting_list=False
        )

        return member

    @classmethod
    def create_member(cls, personal_data, cache: dict):
        now = get_now(cache=cache)
        contracts_signed = {
            contract: now
            for contract in ["sepa_consent", "withdrawal_consent", "privacy_consent"]
        }

        return Member.objects.create(**personal_data, **contracts_signed)

    @classmethod
    def create_coop_shares(
        cls,
        number_of_shares: int,
        member: Member,
        subscriptions: list[Subscription],
        cache: dict,
    ):
        shares_valid_at = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache), apply_buffer_time=True, cache=cache
        )
        if len(subscriptions) > 0:
            shares_valid_at = datetime.date(year=datetime.MAXYEAR, month=12, day=31)
            for subscription in subscriptions:
                shares_valid_at = min(
                    shares_valid_at,
                    TrialPeriodManager.get_end_of_trial_period(
                        subscription=subscription, cache=cache
                    ),
                )

        CoopSharePurchaseHandler.buy_cooperative_shares(
            quantity=number_of_shares,
            member=member,
            shares_valid_at=shares_valid_at,
            cache=cache,
        )

    @classmethod
    def create_subscriptions(
        cls,
        order: TapirOrder,
        member: Member,
        contract_start_date: datetime.date,
        actor: TapirUser,
        cache: dict,
    ):
        _, subscriptions = (
            ApplyTapirOrderManager.apply_order_with_several_product_types(
                member=member,
                order=order,
                contract_start_date=contract_start_date,
                actor=actor,
                needs_admin_confirmation=True,
                cache=cache,
            )
        )

        return subscriptions
