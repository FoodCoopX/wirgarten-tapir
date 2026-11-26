from collections import defaultdict
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Q

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    BreadSpecificsPerDeliveryDay,
)
from tapir.bakery.services.bread_choice_deadline_service import (
    BreadChoiceDeadlineService,
)
from tapir.bakery.services.bread_specifics_service import BreadSpecificsService
from tapir.bakery.services.breaddelivery_service import BreadDeliveryService


@dataclass
class BreadBakedResult:
    created: bool
    deleted: bool
    # Members' choices of the bread on that day, cleared when it stops being
    # baked, or that would be with dry_run.
    cleared_choices: int


@dataclass
class SourceWeek:
    year: int
    delivery_week: int
    bread_count: int


@dataclass
class WeekCopyResult:
    # Days of the target week whose settings were replaced, or would be with
    # dry_run.
    copied_days: list[int]
    # Days of the target week that are over and keep their settings, although
    # the source week has settings for them or they have their own.
    kept_days: list[int]
    # Members' choices of breads the copy stops baking on their day.
    cleared_choices: int


@dataclass
class _CopyPlan:
    source_breads: dict[int, set]
    target_breads: dict[int, set]
    copied_days: list[int]
    kept_days: list[int]
    # Per copied day, the breads the target week stops baking.
    removed_breads: dict[int, set]


class WeeklyPlanService:
    """
    What the weekly bread plan ("Wochenplan Brote") changes: which active
    breads are baked on each delivery day (AvailableBreadsForDeliveryDay)
    and, when a week is copied, their day settings
    (BreadSpecificsPerDeliveryDay).

    The breads of a day that is over
    (BreadChoiceDeadlineService.is_delivery_day_over) no longer change:
    WeeklyPlanValidator refuses switching one on or off, and a copy leaves the
    day alone.

    A bread that stops being baked on a day loses the members' choices of it
    for that day. Its entry is deleted and committed before the choices are
    cleared: a member choosing the bread at that moment waits on the row lock
    BreadChoiceService.check_direct_order_limit takes on the entry, then
    finds it gone, and a choice made before is cleared afterwards. Clearing
    in the same transaction as the delete could deadlock with such a choice,
    which already holds its delivery row.
    """

    @classmethod
    def set_bread_baked(
        cls,
        bread_id: str,
        year: int,
        delivery_week: int,
        delivery_day: int,
        is_baked: bool,
        cache: dict,
        dry_run: bool = False,
    ) -> BreadBakedResult:
        """Expects a day that is not over, see WeeklyPlanValidator."""
        if is_baked:
            if dry_run:
                return BreadBakedResult(created=False, deleted=False, cleared_choices=0)
            _, created = AvailableBreadsForDeliveryDay.objects.get_or_create(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                bread_id=bread_id,
            )
            return BreadBakedResult(created=created, deleted=False, cleared_choices=0)

        removed_breads = {delivery_day: {bread_id}}
        if dry_run:
            return BreadBakedResult(
                created=False,
                deleted=False,
                cleared_choices=cls._count_choices(
                    removed_breads, year, delivery_week, cache=cache
                ),
            )

        deleted_count, _ = AvailableBreadsForDeliveryDay.objects.filter(
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
            bread_id=bread_id,
        ).delete()
        return BreadBakedResult(
            created=False,
            deleted=deleted_count > 0,
            cleared_choices=cls._clear_choices(
                removed_breads, year, delivery_week, cache=cache
            ),
        )

    @classmethod
    def get_source_weeks(
        cls, year: int, delivery_week: int, cache: dict
    ) -> list[SourceWeek]:
        """Weeks before the given one that bake an active bread, latest first."""
        rows = (
            AvailableBreadsForDeliveryDay.objects.filter(bread__is_active=True)
            .filter(Q(year__lt=year) | Q(year=year, delivery_week__lt=delivery_week))
            .values("year", "delivery_week")
            .annotate(bread_count=Count("bread", distinct=True))
            .order_by("-year", "-delivery_week")
        )
        return [SourceWeek(**row) for row in rows]

    @classmethod
    def copy_week(
        cls,
        source_year: int,
        source_week: int,
        target_year: int,
        target_week: int,
        cache: dict,
        dry_run: bool = False,
    ) -> WeekCopyResult:
        """
        On every day it covers, the target week ends up exactly like the
        source week: the same breads baked, with the same day settings. Days
        of the target week that are over keep theirs.
        """
        if dry_run:
            plan = cls._plan_copy(
                source_year, source_week, target_year, target_week, cache=cache
            )
            return WeekCopyResult(
                plan.copied_days,
                plan.kept_days,
                cls._count_choices(
                    plan.removed_breads, target_year, target_week, cache=cache
                ),
            )

        with transaction.atomic():
            # The target week's entries are read under lock, in id order as
            # BreadChoiceService.check_direct_order_limit locks them: a bread
            # switched on or off meanwhile is not missed.
            list(
                AvailableBreadsForDeliveryDay.objects.select_for_update()
                .filter(year=target_year, delivery_week=target_week)
                .order_by("id")
                .values_list("id", flat=True)
            )
            plan = cls._plan_copy(
                source_year, source_week, target_year, target_week, cache=cache
            )
            cls._replace_breads(
                target_year,
                target_week,
                plan.source_breads,
                plan.target_breads,
                plan.copied_days,
            )
            cls._replace_specifics(
                source_year, source_week, target_year, target_week, plan.copied_days
            )

        return WeekCopyResult(
            plan.copied_days,
            plan.kept_days,
            cls._clear_choices(
                plan.removed_breads, target_year, target_week, cache=cache
            ),
        )

    @classmethod
    def _plan_copy(
        cls,
        source_year: int,
        source_week: int,
        target_year: int,
        target_week: int,
        cache: dict,
    ) -> _CopyPlan:
        source_breads = cls._breads_by_day(source_year, source_week)
        target_breads = cls._breads_by_day(target_year, target_week)
        days_with_settings = (
            set(source_breads)
            | set(target_breads)
            | cls._days_with_specifics(source_year, source_week)
            | cls._days_with_specifics(target_year, target_week)
        )
        copied_days = sorted(
            day
            for day in days_with_settings
            if not BreadChoiceDeadlineService.is_delivery_day_over(
                target_year, target_week, day, cache=cache
            )
        )
        return _CopyPlan(
            source_breads=source_breads,
            target_breads=target_breads,
            copied_days=copied_days,
            kept_days=sorted(days_with_settings - set(copied_days)),
            removed_breads={
                day: target_breads[day] - source_breads[day]
                for day in copied_days
                if target_breads[day] - source_breads[day]
            },
        )

    @classmethod
    def _count_choices(
        cls, removed_breads: dict[int, set], year: int, delivery_week: int, cache: dict
    ) -> int:
        return sum(
            len(
                BreadDeliveryService.get_choices_of_breads_for_delivery_day(
                    list(bread_ids), year, delivery_week, day, cache=cache
                )
            )
            for day, bread_ids in removed_breads.items()
        )

    @classmethod
    def _clear_choices(
        cls, removed_breads: dict[int, set], year: int, delivery_week: int, cache: dict
    ) -> int:
        """Call once the entries are deleted and committed, see the class docstring."""
        return sum(
            BreadDeliveryService.clear_choices_of_breads_for_delivery_day(
                list(bread_ids), year, delivery_week, day, cache=cache
            )
            for day, bread_ids in removed_breads.items()
        )

    @classmethod
    def _breads_by_day(cls, year: int, delivery_week: int) -> dict[int, set]:
        breads_by_day = defaultdict(set)
        for day, bread_id in AvailableBreadsForDeliveryDay.objects.filter(
            year=year, delivery_week=delivery_week, bread__is_active=True
        ).values_list("delivery_day", "bread_id"):
            breads_by_day[day].add(bread_id)
        return breads_by_day

    @classmethod
    def _days_with_specifics(cls, year: int, delivery_week: int) -> set[int]:
        return set(
            BreadSpecificsPerDeliveryDay.objects.filter(
                year=year, delivery_week=delivery_week, bread__is_active=True
            ).values_list("delivery_day", flat=True)
        )

    @classmethod
    def _replace_breads(
        cls,
        target_year: int,
        target_week: int,
        source_breads: dict[int, set],
        target_breads: dict[int, set],
        days: list[int],
    ):
        for day in days:
            AvailableBreadsForDeliveryDay.objects.filter(
                year=target_year,
                delivery_week=target_week,
                delivery_day=day,
                bread_id__in=target_breads[day] - source_breads[day],
            ).delete()
        # ignore_conflicts: a bread switched on in the target week meanwhile is
        # already there.
        AvailableBreadsForDeliveryDay.objects.bulk_create(
            [
                AvailableBreadsForDeliveryDay(
                    year=target_year,
                    delivery_week=target_week,
                    delivery_day=day,
                    bread_id=bread_id,
                )
                for day in days
                for bread_id in source_breads[day] - target_breads[day]
            ],
            ignore_conflicts=True,
        )

    @classmethod
    def _replace_specifics(
        cls,
        source_year: int,
        source_week: int,
        target_year: int,
        target_week: int,
        days: list[int],
    ):
        BreadSpecificsPerDeliveryDay.objects.filter(
            year=target_year,
            delivery_week=target_week,
            delivery_day__in=days,
            bread__is_active=True,
        ).delete()
        # ignore_conflicts: settings saved for the target week meanwhile win.
        BreadSpecificsPerDeliveryDay.objects.bulk_create(
            [
                BreadSpecificsPerDeliveryDay(
                    year=target_year,
                    delivery_week=target_week,
                    delivery_day=specifics.delivery_day,
                    bread_id=specifics.bread_id,
                    **{
                        field: getattr(specifics, field)
                        for field in BreadSpecificsService.FIELDS
                    },
                )
                for specifics in BreadSpecificsPerDeliveryDay.objects.filter(
                    year=source_year,
                    delivery_week=source_week,
                    delivery_day__in=days,
                    bread__is_active=True,
                )
            ],
            ignore_conflicts=True,
        )
