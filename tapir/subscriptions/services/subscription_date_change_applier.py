import datetime

from django.core.exceptions import ValidationError

from tapir.accounts.models import TapirUser
from tapir.bakery.services.breaddelivery_service import BreadDeliveryService
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
from tapir.subscriptions.services.renewal_cancellation_status_provider import (
    RenewalCancellationStatusProvider,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.wirgarten.models import (
    Subscription,
    Member,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.utils import get_now, format_date, get_today


class SubscriptionDateChangeApplier:
    ACTION_CHANGE_START = "change_start"
    ACTION_CHANGE_END = "change_end"
    ACTION_CANCEL_RENEWAL = "cancel_renewal"
    ACTIONS = [ACTION_CHANGE_START, ACTION_CHANGE_END, ACTION_CANCEL_RENEWAL]

    @classmethod
    def validate(
        cls,
        subscription: Subscription,
        action: str,
        date: datetime.date | None,
        update_other_contracts: bool,
        cache: dict,
    ):
        if subscription.period.end_date < get_today(cache=cache):
            raise ValidationError(
                "Verträge aus vergangenen Vertragsperioden können nicht geändert werden"
            )

        if update_other_contracts and action == cls.ACTION_CHANGE_START:
            raise ValidationError(
                "Weitere Verträge können nur beim Ändern des Vertragsendes angepasst werden"
            )

        if action == cls.ACTION_CANCEL_RENEWAL:
            cls._validate_renewal_can_be_cancelled(
                subscription=subscription, cache=cache
            )
        elif date is None:
            raise ValidationError("Bitte ein Datum angeben")
        else:
            cls._validate_new_date(
                subscription=subscription, action=action, date=date, cache=cache
            )

        if update_other_contracts:
            cls._validate_other_subscriptions_can_be_ended(
                subscription=subscription,
                end_date=cls._get_end_date_after_change(
                    subscription=subscription, action=action, date=date
                ),
                cache=cache,
            )

    @classmethod
    def _validate_new_date(
        cls, subscription: Subscription, action: str, date: datetime.date, cache: dict
    ):
        period = subscription.period
        if not period.start_date <= date <= period.end_date:
            raise ValidationError("Das Datum muss in der Vertragsperiode liegen")

        if action == cls.ACTION_CHANGE_START:
            if date != period.start_date and date.isoweekday() != 1:
                raise ValidationError(
                    "Der Vertragsbeginn muss ein Montag oder der erste Tag der Vertragsperiode sein"
                )
        elif date != period.end_date and date.isoweekday() != 7:
            raise ValidationError(
                "Das Vertragsende muss ein Sonntag oder der letzte Tag der Vertragsperiode sein"
            )

        start_date, end_date, current_date = (
            (date, subscription.end_date, subscription.start_date)
            if action == cls.ACTION_CHANGE_START
            else (subscription.start_date, date, subscription.end_date)
        )
        if start_date > end_date:
            raise ValidationError(
                f"Das Start-Datum ({format_date(start_date)}) muss vor dem End-Datum ({format_date(end_date)}) liegen."
            )

        if date == current_date:
            raise ValidationError("Keine Änderungen")

        for other_subscription in TapirCache.get_all_subscriptions_for_member(
            member_id=subscription.member_id, cache=cache
        ):
            if (
                other_subscription.id != subscription.id
                and other_subscription.product_id == subscription.product_id
                and other_subscription.start_date <= end_date
                and other_subscription.end_date >= start_date
            ):
                raise ValidationError(
                    f"Der Vertrag würde sich mit dem Vertrag vom {format_date(other_subscription.start_date)} "
                    f"bis {format_date(other_subscription.end_date)} überschneiden."
                )

    @classmethod
    def _validate_other_subscriptions_can_be_ended(
        cls, subscription: Subscription, end_date: datetime.date, cache: dict
    ):
        for other_subscription in cls._get_other_subscriptions_to_end(
            main_subscription=subscription, end_date=end_date, cache=cache
        ):
            if other_subscription.start_date > end_date:
                raise ValidationError(
                    f"Der Vertrag {other_subscription.product.name} beginnt erst am "
                    f"{format_date(other_subscription.start_date)}, nach dem neuen Vertragsende "
                    f"({format_date(end_date)}). Bitte diesen Vertrag separat anpassen."
                )

    @classmethod
    def _get_end_date_after_change(
        cls, subscription: Subscription, action: str, date: datetime.date | None
    ) -> datetime.date:
        if action == cls.ACTION_CHANGE_END:
            return date
        return subscription.end_date

    @classmethod
    def _validate_renewal_can_be_cancelled(
        cls, subscription: Subscription, cache: dict
    ):
        match RenewalCancellationStatusProvider.get_status(
            subscription=subscription, cache=cache
        ):
            case RenewalCancellationStatusProvider.STATUS_AVAILABLE:
                return
            case RenewalCancellationStatusProvider.STATUS_BEFORE_NOTICE_PERIOD_END:
                raise ValidationError(
                    "Die Kündigungsfrist ist noch nicht abgelaufen. "
                    "Kündigungen zum Ende der Vertragsperiode bitte über das Mitgliederprofil eintragen."
                )
            case _:
                raise ValidationError("Dieser Vertrag wird nicht verlängert")

    @classmethod
    def apply_changes(
        cls,
        actor: TapirUser,
        subscription: Subscription,
        action: str,
        date: datetime.date | None,
        update_other_contracts: bool,
        cache: dict,
    ):
        if action == cls.ACTION_CHANGE_START:
            subscription_before = freeze_for_log(subscription)
            subscription.start_date = date
            cls._save_and_log(
                subscription=subscription,
                subscription_before=subscription_before,
                actor=actor,
                cache=cache,
            )
            return

        end_date = cls._get_end_date_after_change(
            subscription=subscription, action=action, date=date
        )
        subscriptions_to_end = [subscription]
        if update_other_contracts:
            subscriptions_to_end.extend(
                cls._get_other_subscriptions_to_end(
                    main_subscription=subscription, end_date=end_date, cache=cache
                )
            )
            cls._end_solidarity_contributions(
                member=subscription.member, end_date=end_date, actor=actor, cache=cache
            )

        not_renewed_subscriptions = []
        for subscription_to_end in subscriptions_to_end:
            not_renewed_subscription = cls._end_subscription(
                subscription=subscription_to_end,
                end_date=end_date,
                actor=actor,
                cache=cache,
            )
            if not_renewed_subscription is not None:
                not_renewed_subscriptions.append(not_renewed_subscription)

        if len(not_renewed_subscriptions) > 0:
            SubscriptionChangeLogEntry().populate_subscription_changed(
                actor=actor,
                user=subscription.member,
                change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.NOT_RENEWED,
                subscriptions=not_renewed_subscriptions,
                admin_confirmed=get_now(cache=cache),
            ).save()

    @classmethod
    def _get_other_subscriptions_to_end(
        cls, main_subscription: Subscription, end_date: datetime.date, cache: dict
    ) -> list[Subscription]:
        # Subscriptions of other products running during the main one and not ending before the new end date
        range_end = max(main_subscription.end_date, end_date)
        return [
            other_subscription
            for other_subscription in TapirCache.get_all_subscriptions_for_member(
                member_id=main_subscription.member_id, cache=cache
            )
            if other_subscription.product_id != main_subscription.product_id
            and other_subscription.start_date <= range_end
            and other_subscription.end_date >= end_date
        ]

    @classmethod
    def _end_subscription(
        cls,
        subscription: Subscription,
        end_date: datetime.date,
        actor: TapirUser,
        cache: dict,
    ) -> Subscription | None:
        # Returns the subscription that won't be renewed because of this change
        subscription_before = freeze_for_log(subscription)
        was_cancelled = subscription.cancellation_ts is not None

        renewal = RenewalCancellationStatusProvider.get_renewal(
            subscription=subscription, cache=cache
        )
        if renewal is not None:
            renewal.delete()

        subscription.cancellation_ts = get_now(cache=cache)
        subscription.end_date = end_date
        cls._save_and_log(
            subscription=subscription,
            subscription_before=subscription_before,
            actor=actor,
            cache=cache,
        )

        if renewal is not None:
            return renewal
        if not was_cancelled:
            return subscription
        return None

    @classmethod
    def _save_and_log(
        cls,
        subscription: Subscription,
        subscription_before: dict,
        actor: TapirUser,
        cache: dict,
    ):
        subscription.save()
        TapirCacheManager.clear_category(
            cache=cache, category=TapirCacheManager.CATEGORY_SUBSCRIPTIONS
        )
        BreadDeliveryService.ensure_bread_deliveries_for_member(
            subscription.member, cache=cache
        )

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
    def _end_solidarity_contributions(
        cls,
        member: Member,
        end_date: datetime.date,
        actor: TapirUser,
        cache: dict,
    ):
        MemberSolidarityContributionService.assign_contribution_to_member(
            member=member,
            actor=actor,
            cache=cache,
            change_date=end_date,
            amount=0,
        )

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            reference_date=end_date,
            actor=actor,
            cache=cache,
            product_type_id_or_soli=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
            comment="Solidarbeitrag End-Datum angepasst zusammen mit Vertrags-End-Datum",
        )
