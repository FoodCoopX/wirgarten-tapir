import datetime

from tapir.accounts.models import TapirUser
from tapir.bakery.services.breaddelivery_service import BreadDeliveryService
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.subscriptions.services.admin_size_change_next_period_finder import (
    AdminSizeChangeNextPeriodFinder,
)
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.subscription_prerequisites_applier import (
    SubscriptionPrerequisitesApplier,
)
from tapir.subscriptions.types import AdminSizeChangeRequest, TapirOrder
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.wirgarten.forms.subscription import cancel_or_delete_subscriptions
from tapir.wirgarten.models import (
    Member,
    ProductType,
    Subscription,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.service.member import send_contract_change_confirmation
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_now


class AdminSizeChangeApplier:
    @classmethod
    def apply_change(
        cls, size_change: AdminSizeChangeRequest, actor: TapirUser, cache: dict
    ) -> list[Subscription]:
        member = size_change.member
        previous_subscription = size_change.subscription
        change_date = size_change.change_date
        order = size_change.order
        prerequisites = size_change.prerequisites

        if prerequisites.desired_pickup_location_id is not None:
            SubscriptionPrerequisitesApplier.apply_pickup_location(
                member=member,
                subscription_start_date=change_date,
                desired_pickup_location_id=prerequisites.desired_pickup_location_id,
                actor=actor,
                cache=cache,
            )

        if change_date > previous_subscription.end_date:
            new_subscriptions = cls.apply_change_from_next_period(
                member=member,
                previous_subscription=previous_subscription,
                change_date=change_date,
                order=order,
                actor=actor,
                cache=cache,
            )
        else:
            new_subscriptions = cls.apply_order_with_next_period_renewals(
                member=member,
                product_type=previous_subscription.product.type,
                change_date=change_date,
                order=order,
                actor=actor,
                cache=cache,
            )

        send_contract_change_confirmation(
            member=member, subs=new_subscriptions, cache=cache
        )

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            actor=actor,
            product_type_id_or_soli=previous_subscription.product.type_id,
            reference_date=change_date,
            comment="Produktanteilsgröße vom Admin durch die Vertragsliste geändert",
            cache=cache,
        )

        SubscriptionPrerequisitesApplier.apply_banking_data(
            member=member,
            iban=prerequisites.iban,
            account_owner=prerequisites.account_owner,
            sepa_allowed=prerequisites.sepa_mandate_confirmed,
            cache=cache,
        )

        return new_subscriptions

    @classmethod
    def apply_order_with_next_period_renewals(
        cls,
        member: Member,
        product_type: ProductType,
        change_date: datetime.date,
        order: TapirOrder,
        actor: TapirUser,
        cache: dict,
    ) -> list[Subscription]:
        ids_of_replaced_subscriptions = list(
            get_active_and_future_subscriptions(reference_date=change_date, cache=cache)
            .filter(member_id=member.id, product__type_id=product_type.id)
            .values_list("id", flat=True)
        )
        next_period_subscriptions_existed = (
            AdminSizeChangeNextPeriodFinder.get_next_period_with_subscriptions(
                member=member,
                product_type_id=product_type.id,
                reference_date=change_date,
                cache=cache,
            )
            is not None
        )

        _, new_subscriptions = ApplyTapirOrderManager.apply_order_single_product_type(
            member=member,
            order=order,
            product_type=product_type,
            contract_start_date=change_date,
            actor=actor,
            needs_admin_confirmation=False,
            cache=cache,
        )

        now = get_now(cache=cache)
        Subscription.objects.filter(
            id__in=[subscription.id for subscription in new_subscriptions]
        ).update(admin_confirmed=now)
        Subscription.objects.filter(id__in=ids_of_replaced_subscriptions).update(
            cancellation_admin_confirmed=now
        )

        if not next_period_subscriptions_existed:
            return new_subscriptions

        renewed_subscriptions = [
            AutomaticSubscriptionRenewalService.build_renewed_subscription(
                subscription=subscription, cache=cache
            )
            for subscription in new_subscriptions
        ]
        return new_subscriptions + cls.save_next_period_subscriptions(
            member=member,
            subscriptions=renewed_subscriptions,
            actor=actor,
            cache=cache,
        )

    @classmethod
    def apply_change_from_next_period(
        cls,
        member: Member,
        previous_subscription: Subscription,
        change_date: datetime.date,
        order: TapirOrder,
        actor: TapirUser,
        cache: dict,
    ) -> list[Subscription]:
        cancel_or_delete_subscriptions(
            member=member,
            start_date=change_date,
            product_type=previous_subscription.product.type,
            actor=actor,
            cache=cache,
        )

        now = get_now(cache=cache)
        previous_subscription.cancellation_ts = now
        previous_subscription.cancellation_admin_confirmed = now
        previous_subscription.save()
        SubscriptionChangeLogEntry().populate_subscription_changed(
            actor=actor,
            user=member,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
            subscriptions=[previous_subscription],
            admin_confirmed=now,
        ).save()

        current_subscriptions_by_product_id = {
            subscription.product_id: subscription
            for subscription in Subscription.objects.filter(
                member_id=member.id,
                product__type_id=previous_subscription.product.type_id,
                start_date__lte=previous_subscription.end_date,
                end_date__gte=previous_subscription.end_date,
            ).select_related("product__type")
        }
        next_period_subscriptions = []
        for product, quantity in order.items():
            subscription = (
                AutomaticSubscriptionRenewalService.build_renewed_subscription(
                    subscription=current_subscriptions_by_product_id.get(
                        product.id, previous_subscription
                    ),
                    cache=cache,
                )
            )
            subscription.product = product
            subscription.quantity = quantity
            subscription.price_override = None
            next_period_subscriptions.append(subscription)

        return cls.save_next_period_subscriptions(
            member=member,
            subscriptions=next_period_subscriptions,
            actor=actor,
            cache=cache,
        )

    @classmethod
    def save_next_period_subscriptions(
        cls,
        member: Member,
        subscriptions: list[Subscription],
        actor: TapirUser,
        cache: dict,
    ) -> list[Subscription]:
        now = get_now(cache=cache)
        for subscription in subscriptions:
            subscription.admin_confirmed = now
            subscription.auto_confirmed = now

        subscriptions = Subscription.objects.bulk_create(subscriptions)
        TapirCacheManager.clear_category(
            cache=cache, category=TapirCacheManager.CATEGORY_SUBSCRIPTIONS
        )
        BreadDeliveryService.ensure_bread_deliveries_for_member(member, cache=cache)

        SubscriptionChangeLogEntry().populate_subscription_changed(
            actor=actor,
            user=member,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.ADDED,
            subscriptions=list(subscriptions),
            admin_confirmed=now,
        ).save()

        return subscriptions
