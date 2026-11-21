from tapir.accounts.models import TapirUser
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.subscription_prerequisites_applier import (
    SubscriptionPrerequisitesApplier,
)
from tapir.subscriptions.types import AdminSubscriptionAddition
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.service.member import send_contract_change_confirmation
from tapir.wirgarten.utils import get_now


class AdminSubscriptionAdditionApplier:
    @classmethod
    def apply_addition(
        cls, addition: AdminSubscriptionAddition, actor: TapirUser, cache: dict
    ) -> list[Subscription]:
        if addition.prerequisites.desired_pickup_location_id is not None:
            SubscriptionPrerequisitesApplier.apply_delivery_address_and_pickup_location(
                member=addition.member,
                subscription_start_date=addition.start_date,
                desired_pickup_location_id=addition.prerequisites.desired_pickup_location_id,
                actor=actor,
                cache=cache,
            )

        new_subscriptions = cls.create_subscription(
            addition=addition, actor=actor, cache=cache
        )

        send_contract_change_confirmation(
            member=addition.member, subs=new_subscriptions, cache=cache
        )

        SubscriptionPrerequisitesApplier.apply_banking_data(
            member=addition.member,
            iban=addition.prerequisites.iban,
            account_owner=addition.prerequisites.account_owner,
            sepa_consent_given=addition.prerequisites.sepa_mandate_confirmed,
            cache=cache,
        )

        return new_subscriptions

    @classmethod
    def create_subscription(
        cls, addition: AdminSubscriptionAddition, actor: TapirUser, cache: dict
    ) -> list[Subscription]:
        trial_disabled, trial_end_date_override = ApplyTapirOrderManager.get_trial_data(
            member=addition.member,
            product_type=addition.product.type,
            contract_start_date=addition.start_date,
            cache=cache,
        )
        new_subscriptions = ApplyTapirOrderManager.create_subscriptions(
            member=addition.member,
            order={addition.product: addition.quantity},
            product_type=addition.product.type,
            contract_start_date=addition.start_date,
            actor=actor,
            needs_admin_confirmation=False,
            trial_disabled=trial_disabled,
            trial_end_date_override=trial_end_date_override,
            cache=cache,
        )
        Subscription.objects.filter(
            id__in=[subscription.id for subscription in new_subscriptions]
        ).update(admin_confirmed=get_now(cache=cache))
        return new_subscriptions
