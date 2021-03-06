import datetime

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from django.views import generic
from django.views.generic import TemplateView

from tapir.accounts.models import TapirUser
from tapir.coop.models import (
    ShareOwner,
    MemberStatus,
    DraftUser,
    ShareOwnership,
    COOP_SHARE_PRICE,
)


class StatisticsView(PermissionRequiredMixin, generic.TemplateView):
    template_name = "coop/statistics.html"
    permission_required = "coop.manage"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        active_members = ShareOwner.objects.with_status(MemberStatus.ACTIVE)
        active_users = TapirUser.objects.filter(share_owner__in=active_members)

        context["active_members"] = active_members.order_by("id")
        context["active_users"] = active_users.order_by("id")
        context["members_missing_accounts"] = active_members.filter(user=None).order_by(
            "id"
        )
        context["applicants"] = DraftUser.objects.order_by("id")

        context["shares"] = self.get_shares_context()
        context["extra_shares"] = self.get_extra_shares_context()
        return context

    @staticmethod
    def get_shares_context():
        context = dict()
        context["nb_share_ownerships_now"] = ShareOwnership.objects.active_temporal(
            timezone.now()
        ).count()
        start_date = ShareOwnership.objects.order_by("start_date").first().start_date
        start_date = datetime.date(day=1, month=start_date.month, year=start_date.year)
        end_date = timezone.now().date()
        end_date = datetime.date(day=1, month=end_date.month, year=end_date.year)
        context["nb_shares_by_month"] = dict()
        current_date = start_date
        while current_date <= end_date:
            context["nb_shares_by_month"][
                current_date
            ] = ShareOwnership.objects.active_temporal(current_date).count()
            if current_date.month < 12:
                current_date = datetime.date(
                    day=1, month=current_date.month + 1, year=current_date.year
                )
            else:
                current_date = datetime.date(day=1, month=1, year=current_date.year + 1)

        nb_months_since_start = (
            (datetime.date.today().year - start_date.year) * 12
            + datetime.date.today().month
            - start_date.month
        )
        context["average_shares_per_month"] = "{:.2f}".format(
            context["nb_share_ownerships_now"] / nb_months_since_start
        )
        context["start_date"] = start_date

        return context

    @staticmethod
    def get_extra_shares_context():
        context = dict()
        threshold_date = datetime.date(day=1, month=1, year=2022)
        first_shares = [
            share_owner.get_oldest_active_share_ownership().id
            for share_owner in ShareOwner.objects.exclude(
                id__in=ShareOwner.objects.with_status(MemberStatus.SOLD)
            )
        ]
        extra_shares = (
            ShareOwnership.objects.filter(start_date__gte=threshold_date)
            .exclude(id__in=first_shares)
            .active_temporal()
        )

        context["threshold_date"] = threshold_date
        context["share_count"] = extra_shares.count()
        context["members"] = ShareOwner.objects.filter(
            share_ownerships__in=extra_shares
        ).distinct()
        members_count = context["members"].count() if context["members"].exists() else 1
        context["average_extra_shares"] = "{:.2f}".format(
            extra_shares.count() / members_count
        )

        total_amount_paid = 0
        total_cost = 0
        paid_percentage = "0%"
        if extra_shares.exists():
            total_amount_paid = extra_shares.aggregate(Sum("amount_paid"))[
                "amount_paid__sum"
            ]
            total_cost = extra_shares.count() * COOP_SHARE_PRICE
            paid_percentage = "{:.0%}".format(total_amount_paid / total_cost)

        context["total_amount_paid"] = total_amount_paid
        context["total_cost"] = total_cost
        context["paid_percentage"] = paid_percentage

        return context


class AboutView(LoginRequiredMixin, TemplateView):
    template_name = "coop/about.html"
