import csv
from urllib.parse import parse_qs, urlencode

from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import OuterRef, Subquery, Sum
from django.forms import CheckboxInput
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, View
from django_filters import BooleanFilter, FilterSet, ModelChoiceFilter, ChoiceFilter
from django_filters.views import FilterView

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    MemberPickupLocation,
    PickupLocation,
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    annotate_member_queryset_with_coop_shares_total_value,
)
from tapir.wirgarten.service.product_standard_order import product_type_order_by
from tapir.wirgarten.utils import format_date, get_now, get_today
from tapir.wirgarten.views.filters import SecondaryOrderingFilter


class ContractUpdatesView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Accounts.MANAGE
    template_name = "wirgarten/subscription/contract_updates.html"


class SubscriptionListFilter(FilterSet):
    """
    Filter set for the subscription list view
    """

    show_only_trial_period = BooleanFilter(
        label=_("Nur Verträge in der Probezeit anzeigen"),
        field_name="show_only_trial_period",
        method="filter_show_only_trial_period",
        widget=CheckboxInput,
    )
    period = ModelChoiceFilter(
        label=_("Vertragsperiode"),
        queryset=GrowingPeriod.objects.all().order_by("-start_date"),
        required=True,
    )
    member = ModelChoiceFilter(
        label=_("Mitglied"),
        queryset=Member.objects.all()
        .order_by("first_name")
        .order_by("last_name")
        .order_by("-created_at"),
    )
    pickup_location = ModelChoiceFilter(
        label=_("Abholort"),
        queryset=PickupLocation.objects.all().order_by("name"),
        method="filter_pickup_location",
    )
    product__type = ModelChoiceFilter(
        label=_("Vertragsart"),
        queryset=ProductType.objects.all().order_by(*product_type_order_by()),
    )
    product = ModelChoiceFilter(label=_("Variante"), queryset=Product.objects.all())
    o = SecondaryOrderingFilter(
        label=_("Sortierung"),
        initial=None,
        choices=(
            ("-created_at", "⮟ Abgeschlossen am"),
            ("created_at", "⮝ Abgeschlossen am"),
            ("-member__member_no", "⮟ Mitgliedsnummer"),
            ("member__member_no", "⮝ Mitgliedsnummer"),
            ("-member__first_name", "⮟ Name"),
            ("member__first_name", "⮝ Name"),
        ),
        required=False,
        empty_label="",
        secondary_ordering="member_id",
    )
    show_only_ended_contracts = BooleanFilter(
        label=_("Nur ausgelaufene Verträge anzeigen"),
        field_name="show_only_ended_contracts",
        method="filter_show_only_ended_contracts",
        widget=CheckboxInput,
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

    def filter_pickup_location(self, queryset, name, value):
        if value:
            # Subquery to get the latest MemberPickupLocation id for each Member
            latest_pickup_location_subquery = Subquery(
                MemberPickupLocation.objects.filter(
                    member_id=OuterRef("member_id"),  # references Member.id
                    valid_from__lte=get_today(),
                )
                .order_by("-valid_from")[:1]
                .values("id")
            )

            # Filter queryset where MemberPickupLocation.id is in the subquery result and the pickup_location matches the value
            return queryset.filter(
                member__memberpickuplocation__id=latest_pickup_location_subquery,
                member__memberpickuplocation__pickup_location_id=value,
            )
        else:
            return queryset.all()

    class Meta:
        model = Subscription
        fields = []

    def __init__(self, data=None, *args, **kwargs):
        def get_default_period_filter_value():
            today = get_today()
            growing_periods = GrowingPeriod.objects.filter(
                start_date__lte=today, end_date__gte=today
            )
            if not growing_periods.exists():
                return None

            return growing_periods.first().id

        if data is None:
            data = {"period": get_default_period_filter_value()}
        else:
            data = data.copy()
            if "period" not in data:
                data["period"] = get_default_period_filter_value()

        super(SubscriptionListFilter, self).__init__(data, *args, **kwargs)

    def filter_show_only_trial_period(self, queryset, name, value):
        if value:
            min_start_date = get_today() + relativedelta(day=1, months=-1)
            return queryset.filter(start_date__gt=min_start_date, cancellation_ts=None)
        return queryset

    def filter_show_only_ended_contracts(self, queryset, name, value):
        today = get_today()
        return (
            queryset.filter(end_date__lt=today)
            if value
            else queryset.filter(end_date__gte=today)
        )

    def filter_membership_type(self, queryset, name, value):
        queryset = annotate_member_queryset_with_coop_shares_total_value(
            queryset, outer_ref="member__id"
        )

        if value == "mitglied":
            return queryset.filter(coop_shares_total_value__gt=0)

        queryset = queryset.filter(coop_shares_total_value__lte=0)
        if value == "student":
            return queryset.filter(member__is_student=True)
        if value == "nicht-mitglied":
            return queryset.filter(member__is_student=False)


class SubscriptionListView(PermissionRequiredMixin, FilterView):
    """
    Lists all subscriptions
    """

    filterset_class = SubscriptionListFilter
    permission_required = Permission.Accounts.VIEW
    template_name = "wirgarten/subscription/subscription_filter.html"
    paginate_by = 20
    model = Subscription

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_query = self.request.GET.urlencode()
        query_dict = parse_qs(filter_query)
        query_dict.pop("page", None)
        new_query_string = urlencode(query_dict, doseq=True)
        context["filter_query"] = new_query_string
        context["today"] = get_today()
        context["total_contracts"] = self.filterset.qs.aggregate(
            total_count=Sum("quantity")
        )["total_count"]

        cache = {}
        subscriptions_trial_end_dates = {}
        if get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache):
            for subscription in self.object_list:
                if TrialPeriodManager.is_contract_in_trial(subscription, cache=cache):
                    subscriptions_trial_end_dates[subscription.id] = (
                        TrialPeriodManager.get_last_day_of_trial_period(
                            subscription, cache=cache
                        )
                    )
        context["subscriptions_trial_end_dates"] = subscriptions_trial_end_dates

        return context

    def get_queryset(self):
        return Subscription.objects.all().order_by("-created_at")


class ExportSubscriptionList(View):
    """
    Exports the filtered subscriptions to csv
    """

    def get(self, request, *args, **kwargs):
        # Get queryset based on filters and ordering
        filter_class = SubscriptionListFilter
        queryset = filter_class(request.GET, queryset=self.get_queryset()).qs

        # Create response object with CSV content
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="Verträge_gefiltert_{get_now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )
        writer = csv.writer(response, delimiter=";", quoting=csv.QUOTE_ALL)

        # Write header row
        writer.writerow(
            [
                "Mitgliedsnr.",
                "Vorname",
                "Nachname",
                "Email",
                "Abgeschlossen am",
                "Gekündigt am",
                "Vertragsbeginn",
                "Vertragsende",
                "Produkt",
                "Variante",
                "Abholort",
            ]
        )

        # Write data rows
        for sub in queryset:
            for _ in range(sub.quantity):
                writer.writerow(
                    [
                        sub.member.member_no,
                        sub.member.first_name,
                        sub.member.last_name,
                        sub.member.email,
                        format_date(sub.created_at),
                        format_date(sub.cancellation_ts),
                        format_date(sub.start_date),
                        format_date(sub.end_date),
                        sub.product.type.name,
                        sub.product.name,
                        (
                            sub.member.pickup_location.name
                            if sub.member.pickup_location
                            else ""
                        ),
                    ]
                )

        return response

    def get_queryset(self):
        return SubscriptionListView.get_queryset(self)

    def get_filterset_class(self):
        return SubscriptionListFilter

    def get_success_url(self):
        return reverse_lazy("subscription_list")
