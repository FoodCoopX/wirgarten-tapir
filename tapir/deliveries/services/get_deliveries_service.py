import datetime

from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, ODD_WEEKS
from tapir.wirgarten.models import Subscription, PickupLocationOpeningTime, Member
from tapir.wirgarten.service.delivery import get_next_delivery_date


class GetDeliveriesService:
    @classmethod
    def get_deliveries(
        cls,
        member: Member,
        limit: int = None,
        date_from: datetime.date = None,
        date_to: datetime.date = None,
    ):
        deliveries = []

        if date_from is None:
            date_from = (
                Subscription.objects.filter(member=member)
                .order_by("start_date")
                .first()
                .start_date
            )

        if date_to is None and limit is None:
            limit = 10

        iteration = 0
        next_delivery_date = get_next_delivery_date(date_from)
        while (date_to is not None and next_delivery_date <= date_to) or (
            limit is not None and iteration < limit
        ):
            delivery_object = cls.build_delivery_object(member, next_delivery_date)
            if delivery_object:
                deliveries.append(delivery_object)

            if limit and iteration >= limit:
                break

            next_delivery_date = get_next_delivery_date(
                next_delivery_date + datetime.timedelta(days=1)
            )
            iteration += 1

        return deliveries

    @classmethod
    def build_delivery_object(cls, member: Member, delivery_date: datetime.date):
        _, week_num, _ = delivery_date.isocalendar()
        even_week = week_num % 2 == 0

        active_subs = Subscription.objects.filter(
            member=member,
            start_date__lte=delivery_date,
            end_date__gte=delivery_date,
            product__type__delivery_cycle__in=[
                WEEKLY[0],
                EVEN_WEEKS[0] if even_week else ODD_WEEKS[0],
            ],
        )

        if not active_subs.exists():
            return None

        pickup_location = member.get_pickup_location(delivery_date)
        opening_times = PickupLocationOpeningTime.objects.filter(
            pickup_location=pickup_location
        )
        delivery_date += datetime.timedelta(
            days=(
                opening_times[0].day_of_week - delivery_date.weekday()
                if opening_times
                else 0
            )
        )

        return {
            "delivery_date": delivery_date,
            "pickup_location": pickup_location,
            "subscriptions": active_subs,
            "pickup_location_opening_times": opening_times,
            "joker_used": cls.is_joker_used_in_week(member, delivery_date),
            "can_joker_be_used": JokerManagementService.can_joker_be_used(
                member, delivery_date
            ),
        }

    @classmethod
    def is_joker_used_in_week(
        cls, member: Member, delivery_date: datetime.date
    ) -> bool:
        week_start = get_monday(delivery_date)
        week_end = week_start + datetime.timedelta(days=6)
        return Joker.objects.filter(
            member=member, date__gte=week_start, date__lte=week_end
        ).exists()
