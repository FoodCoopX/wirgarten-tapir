import datetime

from tapir.accounts.models import TapirUser
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.contract_prerequisites_applier import (
    ContractPrerequisitesApplier,
)
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import Member, ProductType


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
        ContractPrerequisitesApplier.apply_pickup_location(
            member=member,
            contract_start_date=contract_start_date,
            desired_pickup_location_id=desired_pickup_location_id,
            actor=actor,
            cache=cache,
        )

        ContractPrerequisitesApplier.change_payment_rhythm_if_necessary(
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
            coop_share_transaction=None,
            association_membership=None,
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

        ContractPrerequisitesApplier.apply_banking_data(
            member=member,
            iban=iban,
            account_owner=account_owner,
            sepa_allowed=sepa_allowed,
            cache=cache,
        )
