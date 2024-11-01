from datetime import timedelta
from urllib.parse import parse_qs, urlencode

from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import models
from django.db.models import ExpressionWrapper, F, OuterRef, Subquery
from django.db.models.functions import TruncMonth
from django.forms.widgets import Select
from django.utils.translation import gettext_lazy as _
from django_filters import (
    BooleanFilter,
    ChoiceFilter,
    FilterSet,
    ModelChoiceFilter,
    OrderingFilter,
)
from django_filters.views import FilterView

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Member,
    MemberPickupLocation,
    PickupLocation,
)
from tapir.wirgarten.service.member import (
    annotate_member_queryset_with_coop_shares_total_value,
    annotate_member_queryset_with_monthly_payment,
)
from tapir.wirgarten.service.products import get_next_growing_period
from tapir.wirgarten.utils import get_today
from tapir.wirgarten.views.filters import MultiFieldFilter


class ContractStatusFilter(ChoiceFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        if value not in ["Contract Renewed", "Contract Cancelled", "Undecided"]:
            raise ValueError(f"Unknown filter value: {value}")

        # Filter members with an active subscription which is not cancelled
        today = get_today()
        qs = qs.filter(
            subscription__start_date__lte=today,
            subscription__end_date__gte=today,
        )

        if value == "Contract Renewed":
            qs = self.filter_contract_renewed(qs)
        elif value == "Contract Cancelled":
            qs = self.filter_contract_cancelled(qs)
        elif value == "Undecided":
            qs = self.filter_undecided(qs)

        return qs.distinct()

    @staticmethod
    def filter_contract_renewed(qs):
        # Get the upcoming growing period
        growing_period = get_next_growing_period()

        # Filter members with at least one subscription starting in the upcoming growing period
        return qs.filter(
            subscription__start_date__gte=growing_period.start_date,
            subscription__start_date__lte=growing_period.end_date,
        )

    @staticmethod
    def filter_contract_cancelled(qs):
        trial_period_end = ExpressionWrapper(
            TruncMonth(F("subscription__start_date"))
            + timedelta(
                days=30,
            ),
            output_field=models.DateField(),
        )

        return qs.annotate(trial_period_end=trial_period_end).filter(
            subscription__cancellation_ts__gt=F("trial_period_end"),
            subscription__cancellation_ts__isnull=False,
        )

    @staticmethod
    def filter_undecided(qs):
        growing_period = get_next_growing_period()

        # Calculate the trial period start date
        trial_period_start = get_today() + relativedelta(months=-1, day=1)

        # Filter members with no active subscriptions that started within the last month
        qs = qs.filter(subscription__start_date__lte=trial_period_start).exclude(
            subscription__cancellation_ts__isnull=False,
        )

        return qs.exclude(
            subscription__start_date__gte=growing_period.start_date,
            subscription__start_date__lte=growing_period.end_date,
        )


class MemberFilter(FilterSet):
    search = MultiFieldFilter(
        fields=["first_name", "last_name", "email"], label="Suche"
    )
    pickup_location = ModelChoiceFilter(
        label="Abholort",
        queryset=PickupLocation.objects.all().order_by("name"),
        method="filter_pickup_location",
    )
    contract_status = ContractStatusFilter(
        label="Verträge verlängert",
        choices=(
            ("Contract Renewed", "Verträge verlängert"),
            ("Contract Cancelled", "Explizit nicht verlängert"),
            ("Undecided", "Keine Reaktion"),
        ),
    )
    email_verified = BooleanFilter(
        label="Email verifiziert",
        method="filter_email_verified",
        widget=Select(choices=[("", "-----------"), (True, "Ja"), (False, "Nein")]),
    )
    membership_type = ChoiceFilter(
        label="Mitgliedschafts-Typ",
        method="filter_membership_type",
        choices=[
            ("mitglied", "Reguläre Mitglieder"),
            ("student", "Befreit (u.a. Student*innen)"),
            ("nicht-mitglied", "Weder Mitglied noch befreit"),
        ],
    )

    o = OrderingFilter(
        label=_("Sortierung"),
        initial=0,
        choices=(
            ("-member_no", "⮟ Mitgliedsnummer"),
            ("member_no", "⮝ Mitgliedsnummer"),
            ("-first_name", "⮟ Vorname"),
            ("first_name", "⮝ Vorname"),
            ("-last_name", "⮟ Nachname"),
            ("last_name", "⮝ Nachname"),
            ("-email", "⮟ Email"),
            ("email", "⮝ Email"),
            ("created_at", "⮝ Registriert am"),
            ("-created_at", "⮟ Registriert am"),
            ("coop_shares_total_value", "⮝ Genoanteile"),
            ("-coop_shares_total_value", "⮟ Genoanteile"),
            ("monthly_payment", "⮝ Umsatz"),
            ("-monthly_payment", "⮟ Umsatz"),
        ),
        required=True,
        empty_label=None,
    )

    def filter_pickup_location(self, queryset, name, value):
        if value:
            # Subquery to get the latest MemberPickupLocation id for each Member
            today = get_today()
            latest_pickup_location_subquery = Subquery(
                MemberPickupLocation.objects.filter(
                    member_id=OuterRef("id"),  # references Member.id
                    valid_from__lte=today,
                )
                .order_by("-valid_from")[:1]
                .values("id")
            )

            # Filter queryset where MemberPickupLocation.id is in the subquery result and the pickup_location matches the value
            return queryset.filter(
                memberpickuplocation__id=latest_pickup_location_subquery,
                memberpickuplocation__pickup_location_id=value,
            )
        else:
            return queryset.all()

    def filter_email_verified(self, queryset, name, value):
        new_queryset = queryset.all()
        for member in queryset:
            if member.email_verified() != value:
                new_queryset = new_queryset.exclude(id=member.id)
        return new_queryset

    def filter_membership_type(self, queryset, name, value):
        if value == "mitglied":
            return queryset.filter(coop_shares_total_value__gt=0)

        queryset = queryset.filter(coop_shares_total_value__lte=0)
        if value == "student":
            return queryset.filter(is_student=True)
        if value == "nicht-mitglied":
            return queryset.filter(is_student=False)

    def __init__(self, data=None, *args, **kwargs):
        if data is None:
            data = {"o": "-created_at"}
        else:
            data = data.copy()

            if "o" not in data:
                data["o"] = "-created_at"

        super(MemberFilter, self).__init__(data, *args, **kwargs)

        if get_next_growing_period() is None:
            w = self.form.fields["contract_status"].widget
            w.attrs["disabled"] = True
            w.attrs["title"] = "Es gibt noch keine neue Vertragsperiode!"


class MemberListView(PermissionRequiredMixin, FilterView):
    filterset_class = MemberFilter
    permission_required = Permission.Accounts.VIEW
    template_name = "wirgarten/member/member_filter.html"
    paginate_by = 20
    model = Member

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_query = self.request.GET.urlencode()
        query_dict = parse_qs(filter_query)
        query_dict.pop("page", None)
        new_query_string = urlencode(query_dict, doseq=True)
        context["filter_query"] = new_query_string
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = annotate_member_queryset_with_coop_shares_total_value(queryset)
        queryset = annotate_member_queryset_with_monthly_payment(queryset)

        return queryset
