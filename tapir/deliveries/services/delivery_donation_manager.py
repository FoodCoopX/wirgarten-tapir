import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.config import (
    DELIVERY_DONATION_MODE_DISABLED,
    DELIVERY_DONATION_MODE_ONLY_AFTER_JOKERS,
)
from tapir.deliveries.models import DeliveryDonation
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.subscriptions.services.subscription_delivered_in_week_checked import (
    SubscriptionDeliveredInWeekChecker,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class DeliveryDonationManager:
    @classmethod
    def can_delivery_be_donated(
        cls, member: Member, delivery_date: datetime.date, cache: dict
    ):
        mode = get_parameter_value(
            key=ParameterKeys.DELIVERY_DONATION_MODE, cache=cache
        )
        if mode == DELIVERY_DONATION_MODE_DISABLED:
            return False

        if (
            mode == DELIVERY_DONATION_MODE_ONLY_AFTER_JOKERS
            and JokerManagementService.can_joker_be_used_in_week(
                member=member, reference_date=delivery_date, cache=cache
            )
        ):
            return False

        if JokerManagementService.does_member_have_a_joker_in_week(
            member=member, reference_date=delivery_date, cache=cache
        ):
            return False

        if not JokerManagementService.can_joker_be_used_relative_to_date_limit(
            reference_date=delivery_date, cache=cache
        ):
            return False

        return cls.does_member_have_at_least_one_subscription_delivered_at_date(
            member_id=member.id, delivery_date=delivery_date, cache=cache
        )

    @classmethod
    def does_member_have_at_least_one_subscription_delivered_at_date(
        cls, member_id: str, delivery_date: datetime.date, cache: dict
    ):
        subscriptions = TapirCache.get_subscriptions_active_at_date(
            reference_date=delivery_date, cache=cache
        )

        for subscription in subscriptions:
            if subscription.member_id != member_id:
                continue

            if SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
                subscription=subscription, delivery_date=delivery_date, cache=cache
            ):
                return True

        return False

    @classmethod
    def does_member_have_a_donation_in_week(
        cls, member: Member, reference_date: datetime.date, cache: dict
    ):
        if (
            get_parameter_value(ParameterKeys.DELIVERY_DONATION_MODE, cache=cache)
            == DELIVERY_DONATION_MODE_DISABLED
        ):
            return False

        donations = TapirCache.get_all_delivery_donations_for_member(
            member_id=member.id, cache=cache
        )
        for donation in donations:
            if (
                donation.date.isocalendar().week == reference_date.isocalendar().week
                and donation.date.year == reference_date.isocalendar().year
            ):
                return True
            if donation.date > reference_date:
                # donations are sorted by date,
                # if we reach a joker that is past our given date we know we won't find one for the given date
                return False

        return False

    @classmethod
    def can_donation_be_cancelled(cls, donation: DeliveryDonation, cache: dict) -> bool:
        return get_today(
            cache=cache
        ) <= JokerManagementService.get_date_limit_for_joker_changes(
            reference_date=donation.date, cache=cache
        )

    @classmethod
    def cancel_donation(cls, donation: DeliveryDonation):
        donation.delete()
