import datetime
import re
from dataclasses import dataclass
from typing import List

from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.deliveries.services.weeks_without_delivery_service import (
    WeeksWithoutDeliveryService,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_current_growing_period
from tapir.wirgarten.utils import get_today


class JokerManagementService:
    @dataclass
    class JokerRestriction:
        start_day: int
        start_month: int
        end_day: int
        end_month: int
        max_jokers: int

    @classmethod
    def get_date_limit_for_joker_changes(cls, reference_date: datetime.date):
        return DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
            reference_date
        )

    @classmethod
    def can_joker_be_used_relative_to_date_limit(
        cls, reference_date: datetime.date
    ) -> bool:
        return cls.get_date_limit_for_joker_changes(reference_date) > get_today()

    @classmethod
    def can_joker_be_used_relative_to_max_amount_per_growing_period(
        cls, member: Member, reference_date: datetime.date
    ) -> bool:
        growing_period = get_current_growing_period(reference_date)
        if not growing_period:
            return False

        nb_used_jokers_in_growing_period = Joker.objects.filter(
            member=member,
            date__gte=growing_period.start_date,
            date__lte=growing_period.end_date,
        ).count()

        return nb_used_jokers_in_growing_period < get_parameter_value(
            Parameter.JOKERS_AMOUNT_PER_CONTRACT
        )

    @classmethod
    def can_joker_be_cancelled(cls, joker: Joker) -> bool:
        return get_today() <= cls.get_date_limit_for_joker_changes(joker.date)

    @classmethod
    def cancel_joker(cls, joker: Joker):
        joker.delete()

    @classmethod
    def can_joker_be_used_in_week(
        cls, member: Member, reference_date: datetime.date
    ) -> bool:
        return (
            not cls.does_member_have_a_joker_in_week(member, reference_date)
            and cls.can_joker_be_used_relative_to_date_limit(reference_date)
            and cls.can_joker_be_used_relative_to_max_amount_per_growing_period(
                member, reference_date
            )
            and cls.can_joker_be_used_relative_to_restrictions(member, reference_date)
            and cls.can_joker_be_used_relative_to_weeks_without_delivery(reference_date)
        )

    @classmethod
    def does_member_have_a_joker_in_week(
        cls, member: Member, reference_date: datetime.date
    ) -> bool:
        return Joker.objects.filter(
            member=member,
            date__week=reference_date.isocalendar().week,
            date__year=reference_date.year,
        ).exists()

    @classmethod
    def get_extra_joker_restrictions(
        cls, restrictions_as_string: str = None
    ) -> List[JokerRestriction]:
        if restrictions_as_string is None:
            restrictions_as_string = get_parameter_value(Parameter.JOKERS_RESTRICTIONS)

        if restrictions_as_string == "disabled":
            return []

        restrictions = []
        for restriction_as_string in restrictions_as_string.split(";"):
            if restriction_as_string.strip() == "":
                continue

            # Example: 13.04.-25.06.[12]
            result = re.search(
                r"(\d+)\.(\d+)\.-(\d+)\.(\d+)\.\[(\d+)]", restriction_as_string
            )
            if result is None:
                raise ValidationError(
                    f"Invalid restriction given: {restriction_as_string}"
                )

            (
                start_day_as_string,
                start_month_as_string,
                end_day_as_string,
                end_month_as_string,
                max_jokers_as_string,
            ) = result.groups()

            restrictions.append(
                cls.JokerRestriction(
                    start_day=int(start_day_as_string),
                    start_month=int(start_month_as_string),
                    end_day=int(end_day_as_string),
                    end_month=int(end_month_as_string),
                    max_jokers=int(max_jokers_as_string),
                )
            )

        return restrictions

    @classmethod
    def validate_joker_restrictions(cls, restrictions_as_string: str):
        try:
            cls.get_extra_joker_restrictions(restrictions_as_string)
        except Exception as e:
            raise ValidationError(f"Invalid joker restriction value: {e}")

    @classmethod
    def can_joker_be_used_relative_to_restrictions(
        cls, member: Member, reference_date: datetime.date
    ) -> bool:
        restrictions = cls.get_extra_joker_restrictions()
        for restriction in restrictions:
            restriction_start_date = datetime.date(
                year=reference_date.year,
                month=restriction.start_month,
                day=restriction.start_day,
            )
            if restriction_start_date > reference_date:
                continue

            restriction_end_date = datetime.date(
                year=reference_date.year,
                month=restriction.end_month,
                day=restriction.end_day,
            )
            if restriction_end_date < reference_date:
                continue

            if (
                Joker.objects.filter(
                    member=member,
                    date__gte=restriction_start_date,
                    date__lte=restriction_end_date,
                ).count()
                >= restriction.max_jokers
            ):
                return False

        return True

    @staticmethod
    def can_joker_be_used_relative_to_weeks_without_delivery(
        reference_date: datetime.date,
    ) -> bool:
        return not WeeksWithoutDeliveryService.is_delivery_cancelled_this_week(
            reference_date
        )
