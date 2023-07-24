from urllib.parse import parse_qs, urlencode
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.forms import CheckboxInput
from django.db.models import (
    Sum,
    Subquery,
    OuterRef,
)
from django_filters import FilterSet, BooleanFilter, ModelChoiceFilter
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    CoopShareTransaction,
    GrowingPeriod,
    MemberPickupLocation,
    Subscription,
    Member,
    PickupLocation,
    ProductType,
    Product,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    product_type_order_by,
)
from dateutil.relativedelta import relativedelta
from tapir.wirgarten.utils import get_now, get_today
from tapir.wirgarten.views.filters import SecondaryOrderingFilter
from django_filters.views import FilterView


class NewContractsView(PermissionRequiredMixin, TemplateView):
    """
    Displays a list of all new contracts that are not confirmed by the admin yet
    """

    template_name = "wirgarten/subscription/new_contracts_overview.html"
    permission_required = "accounts.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        coop_shares = CoopShareTransaction.objects.filter(
            admin_confirmed__isnull=True,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        ).order_by("timestamp")

        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        harvest_shares = Subscription.objects.filter(
            admin_confirmed__isnull=True, product__type_id=base_product_type_id
        ).order_by("created_at")

        additional_shares = (
            Subscription.objects.filter(admin_confirmed__isnull=True)
            .exclude(product__type_id=base_product_type_id)
            .order_by("created_at")
        )

        context["new_harvest_and_coop_shares"] = harvest_shares
        context["new_coop_shares"] = coop_shares
        context["new_additional_shares"] = additional_shares
        return context


@permission_required("accounts.manage")
@transaction.atomic
def confirm_new_contracts(request, **kwargs):
    """
    Admin action to confirm the selected contracts
    """

    query_dict = dict(x.split("=") for x in request.environ["QUERY_STRING"].split("&"))
    for key, val in query_dict.items():
        query_dict[key] = val.split(",")

    harvest_and_coop_shares = query_dict.pop("new_harvest_and_coop_shares", [])
    additional_shares = query_dict.pop("new_additional_shares", [])
    subscription_ids = harvest_and_coop_shares + additional_shares
    now = get_now()
    if len(subscription_ids):
        Subscription.objects.filter(id__in=subscription_ids).update(admin_confirmed=now)

    coop_shares = query_dict.pop("new_coop_shares", [])
    if len(coop_shares):
        CoopShareTransaction.objects.filter(id__in=coop_shares).update(
            admin_confirmed=now
        )

    return HttpResponseRedirect(reverse_lazy("wirgarten:new_contracts"))


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
        label=_("Anbauperiode"),
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
            ("-solidarity_price", "⮟ Solidarpreis"),
            ("solidarity_price", "⮝ Solidarpreis"),
        ),
        required=False,
        empty_label="",
        secondary_ordering="member_id",
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
            return (
                GrowingPeriod.objects.filter(start_date__lte=today, end_date__gte=today)
                .first()
                .id
            )

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
        return context
