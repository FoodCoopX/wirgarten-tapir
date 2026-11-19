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
from tapir.wirgarten.models import Member, Subscription
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_now


class AdminSizeChangeApplier:
    @classmethod
    def apply_change(
        cls,
        member: Member,
        previous_subscription: Subscription,
        change_date: datetime.date,
        order: TapirOrder,
        actor: TapirUser,
        desired_pickup_location_id: str | None,
        payment_rhythm: str | None,
        iban: str,
        account_owner: str,
        sepa_mandate_confirmed: bool,
        cache: dict,
    ) -> list[Subscription]:
        if desired_pickup_location_id is not None:
            ContractPrerequisitesApplier.apply_pickup_location(
                member=member,
                contract_start_date=change_date,
                desired_pickup_location_id=desired_pickup_location_id,
                actor=actor,
                cache=cache,
            )

        ContractPrerequisitesApplier.change_payment_rhythm_if_necessary(
            payment_rhythm=payment_rhythm, member=member, actor=actor, cache=cache
        )

        product_type = previous_subscription.product.type
        ids_of_replaced_subscriptions = list(
            get_active_and_future_subscriptions(reference_date=change_date, cache=cache)
            .filter(member_id=member.id, product__type_id=product_type.id)
            .values_list("id", flat=True)
        )

        subscriptions_existed_before_changes, new_subscriptions = (
            ApplyTapirOrderManager.apply_order_single_product_type(
                member=member,
                order=order,
                product_type=product_type,
                contract_start_date=change_date,
                actor=actor,
                needs_admin_confirmation=False,
                cache=cache,
            )
        )

        Subscription.objects.filter(
            id__in=ids_of_replaced_subscriptions,
            cancellation_ts__isnull=False,
            cancellation_admin_confirmed__isnull=True,
        ).update(cancellation_admin_confirmed=get_now(cache=cache))

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
            reference_date=change_date,
            comment="Produktanteilsgröße vom Admin durch die Vertragsliste geändert",
            cache=cache,
        )

        ContractPrerequisitesApplier.apply_banking_data(
            member=member,
            iban=iban,
            account_owner=account_owner,
            sepa_allowed=sepa_mandate_confirmed,
            cache=cache,
        )

        return new_subscriptions
