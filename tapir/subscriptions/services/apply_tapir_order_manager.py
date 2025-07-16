import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.forms.subscription import cancel_or_delete_subscriptions
from tapir.wirgarten.models import ProductType, Member, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    get_or_create_mandate_ref,
    send_contract_change_confirmation,
    send_order_confirmation,
)
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
    get_active_subscriptions,
    get_current_growing_period,
)
from tapir.wirgarten.utils import get_now


class ApplyTapirOrderManager:
    @classmethod
    def apply_order_single_product_type(
        cls,
        member: Member,
        order: TapirOrder,
        product_type: ProductType,
        contract_start_date: datetime.date,
        cache: dict,
    ):
        active_and_future_subscriptions = get_active_and_future_subscriptions(
            reference_date=contract_start_date, cache=cache
        ).filter(member=member, product__type_id=product_type.id)
        subscriptions_existed_before_changes = active_and_future_subscriptions.exists()

        earliest_trial_period_end_date = None
        active_subscriptions_exists = get_active_subscriptions(
            reference_date=contract_start_date, cache=cache
        ).filter(id__in=active_and_future_subscriptions.values_list("id", flat=True))
        if active_subscriptions_exists:
            earliest_trial_period_end_date = (
                TrialPeriodManager.get_earliest_trial_period_end_date_for_product_type(
                    member_id=member.id,
                    product_type_id=product_type.id,
                    reference_date=contract_start_date,
                    cache=cache,
                )
            )
        cancel_or_delete_subscriptions(
            member_id=member.id,
            product_type=product_type,
            start_date=contract_start_date,
            cache=cache,
        )
        TapirCache.clear_category(cache=cache, category="subscriptions")

        growing_period = get_current_growing_period(
            reference_date=contract_start_date, cache=cache
        )

        notice_period_duration = None
        if get_parameter_value(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
        ):
            notice_period_duration = NoticePeriodManager.get_notice_period_duration(
                product_type=product_type,
                growing_period=growing_period,
                cache=cache,
            )

        contract_end_date = None
        if product_type.subscriptions_have_end_dates:
            contract_end_date = growing_period.end_date

        now = get_now(cache=cache)
        trial_disabled = (
            active_subscriptions_exists
            and earliest_trial_period_end_date is None
            or not get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache)
        )
        subscriptions = []
        for product, quantity in order.items():
            subscriptions.append(
                Subscription(
                    member=member,
                    product=product,
                    period=growing_period,
                    quantity=quantity,
                    start_date=contract_start_date,
                    end_date=contract_end_date,
                    cancellation_ts=None,
                    solidarity_price_percentage=None,
                    solidarity_price_absolute=None,
                    mandate_ref=get_or_create_mandate_ref(member=member, cache=cache),
                    consent_ts=now,
                    withdrawal_consent_ts=now,
                    trial_disabled=trial_disabled,
                    trial_end_date_override=earliest_trial_period_end_date,
                    notice_period_duration=notice_period_duration,
                )
            )

        new_subscriptions = Subscription.objects.bulk_create(subscriptions)
        TapirCache.clear_category(cache=cache, category="subscriptions")

        return subscriptions_existed_before_changes, new_subscriptions

    @classmethod
    def apply_order_with_several_product_types(
        cls,
        member: Member,
        order: TapirOrder,
        contract_start_date: datetime.date,
        cache: dict,
    ) -> (bool, list[Subscription]):
        orders_by_product_type = {}
        subscriptions_existed_before_changes = False
        new_subscriptions = []

        for product, quantity in order.items():
            if product.type not in orders_by_product_type.keys():
                orders_by_product_type[product.type] = {}
            orders_by_product_type[product.type][product] = quantity

        for product_type, order in orders_by_product_type.items():
            (
                subscriptions_of_this_product_type_existed_before_changes,
                new_subscriptions_of_this_product_type,
            ) = ApplyTapirOrderManager.apply_order_single_product_type(
                member=member,
                order=order,
                product_type=product_type,
                contract_start_date=contract_start_date,
                cache=cache,
            )
            subscriptions_existed_before_changes = (
                subscriptions_existed_before_changes
                or subscriptions_of_this_product_type_existed_before_changes
            )
            new_subscriptions.extend(new_subscriptions_of_this_product_type)

        return subscriptions_existed_before_changes, new_subscriptions

    @classmethod
    def send_appropriate_mail(
        cls,
        subscriptions_existed_before_changes: bool,
        member: Member,
        new_subscriptions: list[Subscription],
        cache: dict,
    ):
        if subscriptions_existed_before_changes:
            send_contract_change_confirmation(
                member=member, subs=new_subscriptions, cache=cache
            )
        else:
            send_order_confirmation(member=member, subs=new_subscriptions, cache=cache)
