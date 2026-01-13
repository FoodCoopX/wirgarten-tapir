import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.config import DELIVERY_DONATION_MODE_DISABLED
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys


class SubscriptionDeliveredInWeekChecker:
    @classmethod
    def is_subscription_delivered_in_week(
        cls, subscription: Subscription, delivery_date: datetime.date, cache: dict
    ):
        if not DeliveryDateCalculator.is_week_delivered(
            delivery_cycle=subscription.product.type.delivery_cycle,
            delivery_date=delivery_date,
            check_for_weeks_without_delivery=True,
            cache=cache,
        ):
            return False

        if get_parameter_value(
            key=ParameterKeys.JOKERS_ENABLED, cache=cache
        ) and JokerManagementService.does_member_have_a_joker_in_week(
            member=subscription.member, reference_date=delivery_date, cache=cache
        ):
            return False

        from tapir.deliveries.services.delivery_donation_manager import (
            DeliveryDonationManager,
        )

        if get_parameter_value(
            key=ParameterKeys.DELIVERY_DONATION_MODE, cache=cache
        ) != DELIVERY_DONATION_MODE_DISABLED and DeliveryDonationManager.does_member_have_a_donation_in_week(
            member=subscription.member, reference_date=delivery_date, cache=cache
        ):
            return False

        return True
