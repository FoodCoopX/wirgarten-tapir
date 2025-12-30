import datetime

from icecream import ic

from tapir.accounts.models import TapirUser
from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.solidarity_contribution.models import SolidarityContribution
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
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    Member,
    Subscription,
    QuestionaireTrafficSourceResponse,
    QuestionaireTrafficSourceOption,
)
from tapir.wirgarten.service.member import (
    send_product_order_confirmation,
    send_investing_membership_confirmation,
)
from tapir.wirgarten.service.products import get_next_growing_period
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
        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            validated_serializer_data["shopping_cart_order"], cache=cache
        )
        pickup_location = None
        if OrderValidator.does_order_need_a_pickup_location(order=order, cache=cache):
            pickup_location = BestellWizardOrderValidator.get_first_pickup_location_with_enough_capacity(
                pickup_location_ids=validated_serializer_data["pickup_location_ids"],
                contract_start_date=contract_start_date,
                member=None,
                order=order,
                cache=cache,
            )

        is_student = validated_serializer_data["student_status_enabled"]
        member = cls.create_member(
            personal_data=validated_serializer_data["personal_data"],
            is_student=is_student,
            cache=cache,
        )
        actor = request.user if request.user.is_authenticated else member
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=validated_serializer_data["payment_rhythm"],
            valid_from=get_today(cache=cache),
            cache=cache,
            actor=actor,
        )

        subscriptions = cls.create_subscriptions(
            order=order,
            member=member,
            actor=actor,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        if OrderValidator.does_order_need_a_pickup_location(order=order, cache=cache):
            MemberPickupLocationService.link_member_to_pickup_location(
                pickup_location_id=pickup_location.id,
                member=member,
                valid_from=contract_start_date,
                actor=actor,
                cache=cache,
            )

        coop_share_transaction = None
        if legal_status_is_cooperative(cache=cache) and not is_student:
            coop_share_transaction = cls.create_coop_shares(
                number_of_shares=validated_serializer_data["number_of_coop_shares"],
                member=member,
                subscriptions=subscriptions,
                cache=cache,
                actor=actor,
            )

        solidarity_contribution_start_date = contract_start_date
        if len(subscriptions) == 0 and coop_share_transaction is not None:
            ic("PROUT")
            solidarity_contribution_start_date = coop_share_transaction.valid_at
        ic(contract_start_date, solidarity_contribution_start_date)
        cls.create_solidarity_contribution(
            member=member,
            contribution=validated_serializer_data["solidarity_contribution"],
            contract_start_date=solidarity_contribution_start_date,
            cache=cache,
        )

        cls.create_questionnaire_responses(
            questionnaire_source_ids=validated_serializer_data["distribution_channels"],
            member_id=member.id,
        )

        if coop_share_transaction is not None and len(subscriptions) == 0:
            send_investing_membership_confirmation(
                member_id=member.id, coop_share_transaction=coop_share_transaction
            )
        else:
            send_product_order_confirmation(
                member, subscriptions, cache=cache, from_waiting_list=False
            )

        return member

    @classmethod
    def create_questionnaire_responses(
        cls, questionnaire_source_ids: list[str], member_id: str
    ):
        response = QuestionaireTrafficSourceResponse.objects.create(member_id=member_id)
        sources = QuestionaireTrafficSourceOption.objects.filter(
            id__in=questionnaire_source_ids
        )
        response.sources.set(sources)

    @classmethod
    def create_member(cls, personal_data, is_student: bool, cache: dict):
        now = get_now(cache=cache)
        contracts_signed = dict.fromkeys(
            ["sepa_consent", "withdrawal_consent", "privacy_consent"], now
        )

        return Member.objects.create(
            **personal_data, **contracts_signed, is_student=is_student
        )

    @classmethod
    def create_coop_shares(
        cls,
        number_of_shares: int,
        member: Member,
        subscriptions: list[Subscription],
        cache: dict,
        actor: TapirUser,
    ):
        shares_valid_at = datetime.date(year=datetime.MAXYEAR, month=12, day=31)
        at_least_one_trial_period_found = False
        if len(subscriptions) > 0:
            for subscription in subscriptions:
                end_of_trial_period = TrialPeriodManager.get_end_of_trial_period(
                    obj=subscription, cache=cache
                )
                if end_of_trial_period is not None:
                    shares_valid_at = min(
                        shares_valid_at,
                        TrialPeriodManager.get_end_of_trial_period(
                            obj=subscription, cache=cache
                        ),
                    )
                    at_least_one_trial_period_found = True

        if not at_least_one_trial_period_found:
            shares_valid_at = ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache), apply_buffer_time=True, cache=cache
            )

        return CoopSharePurchaseHandler.buy_cooperative_shares(
            quantity=number_of_shares,
            member=member,
            shares_valid_at=shares_valid_at,
            cache=cache,
            actor=actor,
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

    @classmethod
    def create_solidarity_contribution(
        cls,
        member: Member,
        contribution: float,
        contract_start_date: datetime.date,
        cache: dict,
    ):
        if contribution == 0:
            return

        growing_period_current = TapirCache.get_growing_period_at_date(
            reference_date=contract_start_date, cache=cache
        )
        if growing_period_current is None:
            soli_end_date = get_next_growing_period(
                reference_date=contract_start_date, cache=cache
            ).start_date - datetime.timedelta(days=1)
        else:
            soli_end_date = growing_period_current.end_date

        SolidarityContribution.objects.create(
            member=member,
            amount=contribution,
            start_date=contract_start_date,
            end_date=soli_end_date,
        )
