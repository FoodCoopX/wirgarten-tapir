import datetime

from django.core.exceptions import ValidationError

from tapir.accounts.models import TapirUser
from tapir.log.util import freeze_for_log
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.models import (
    SubscriptionChangedLogEntry,
)
from tapir.utils.services.model_date_range_overlap_checker import (
    ModelDateRangeOverlapChecker,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.wirgarten.models import (
    Subscription,
    Member,
)
from tapir.wirgarten.utils import get_now, format_date, get_today


class SubscriptionDateChangeApplier:
    @classmethod
    def apply_changes(
        cls,
        actor: TapirUser,
        start_date: datetime.date,
        end_date: datetime.date,
        update_end_date_of_other_contracts: bool,
        subscription: Subscription,
        cache: dict,
    ):
        start_date_before_changes = subscription.start_date
        end_date_before_changes = subscription.end_date

        cls._set_end_date_and_cancel_and_create_log_entry_and_create_credit(
            subscription=subscription,
            start_date_after_changes=start_date,
            end_date_after_changes=end_date,
            actor=actor,
            cache=cache,
        )

        if update_end_date_of_other_contracts:
            cls._update_solidarity_contributions(
                member=subscription.member,
                end_date_after_changes=subscription.end_date,
                actor=actor,
                cache=cache,
            )

            cls._update_other_subscriptions(
                main_subscription=subscription,
                start_date_before_changes=start_date_before_changes,
                end_date_before_changes=end_date_before_changes,
                start_date_after_changes=subscription.start_date,
                end_date_after_changes=subscription.end_date,
                actor=actor,
                cache=cache,
            )

    @classmethod
    def validate_dates(
        cls,
        subscription: Subscription,
        start_date: datetime.date,
        end_date: datetime.date,
        cache: dict,
    ):
        if start_date > end_date:
            raise ValidationError(
                f"Das Start-Datum ({format_date(start_date)}) muss vor dem End-Datum ({format_date(end_date)}) liegen."
            )

        if subscription.start_date == start_date and subscription.end_date == end_date:
            raise ValidationError("Keine Änderungen")

        if TapirCache.get_growing_period_at_date(
            subscription.start_date, cache=cache
        ) != TapirCache.get_growing_period_at_date(start_date, cache=cache):
            raise ValidationError(
                "Das neue Start-Datum muss im gleiche Vertragsperiode liegen wie das alte"
            )

        if TapirCache.get_growing_period_at_date(
            subscription.end_date, cache=cache
        ) != TapirCache.get_growing_period_at_date(end_date, cache=cache):
            raise ValidationError(
                "Das neue End-Datum muss im gleiche Vertragsperiode liegen wie das alte"
            )

    @classmethod
    def _update_other_subscriptions(
        cls,
        main_subscription: Subscription,
        start_date_before_changes: datetime.date,
        start_date_after_changes: datetime.date,
        end_date_before_changes: datetime.date,
        end_date_after_changes: datetime.date,
        actor: TapirUser,
        cache: dict,
    ):
        range_start = min(
            start_date_before_changes,
            start_date_after_changes,
            end_date_before_changes,
            end_date_after_changes,
        )
        range_end = max(
            start_date_before_changes,
            start_date_after_changes,
            end_date_before_changes,
            end_date_after_changes,
        )
        member_subscriptions = Subscription.objects.filter(
            member_id=main_subscription.member_id
        ).exclude(id=main_subscription.id)
        relevant_subscriptions = (
            ModelDateRangeOverlapChecker.filter_objects_that_overlap_with_range(
                queryset=member_subscriptions,
                range_start=range_start,
                range_end=range_end,
            )
        )

        subscribed_product_ids = set(
            relevant_subscriptions.values_list("product_id", flat=True).distinct()
        )

        for product_in in subscribed_product_ids:
            earliest_subscription = (
                relevant_subscriptions.filter(product_id=product_in)
                .order_by("start_date")
                .first()
            )
            cls._set_end_date_and_cancel_and_create_log_entry_and_create_credit(
                actor=actor,
                cache=cache,
                subscription=earliest_subscription,
                start_date_after_changes=None,
                end_date_after_changes=end_date_after_changes,
            )

    @classmethod
    def _set_end_date_and_cancel_and_create_log_entry_and_create_credit(
        cls,
        actor: TapirUser,
        cache: dict,
        subscription: Subscription,
        start_date_after_changes: datetime.date | None,
        end_date_after_changes: datetime.date,
    ):
        subscription_before = freeze_for_log(subscription)
        if start_date_after_changes is not None:
            subscription.start_date = start_date_after_changes
        if end_date_after_changes != subscription.end_date:
            subscription.cancellation_ts = get_now(cache=cache)
            Subscription.objects.exclude(id=subscription.id).filter(
                member_id=subscription.member_id,
                product_id=subscription.product_id,
                end_date__gt=end_date_after_changes,
            ).delete()

        subscription.end_date = end_date_after_changes
        subscription.save()
        TapirCacheManager.clear_category(cache=cache, category="subscriptions")

        SubscriptionChangedLogEntry().populate(
            old_frozen=subscription_before,
            new_model=subscription,
            user=subscription.member,
            actor=actor,
        ).save()

        MemberCreditCreator.create_member_credit_if_necessary(
            member=subscription.member,
            reference_date=get_today(cache=cache),
            actor=actor,
            cache=cache,
            product_type_id_or_soli=subscription.product.type.id,
            comment=f"Vertragsdaten vom Admin durch der Vertragsliste angepasst. Vertrag: {subscription.long_str()}",
        )

    @classmethod
    def _update_solidarity_contributions(
        cls,
        member: Member,
        end_date_after_changes: datetime.date,
        actor: TapirUser,
        cache: dict,
    ):
        MemberSolidarityContributionService.assign_contribution_to_member(
            member=member,
            actor=actor,
            cache=cache,
            change_date=end_date_after_changes,
            amount=0,
        )

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            reference_date=end_date_after_changes,
            actor=actor,
            cache=cache,
            product_type_id_or_soli=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
            comment="Solidarbeitrag End-Datum angepasst zusammen mit Vertrags-End-Datum",
        )
