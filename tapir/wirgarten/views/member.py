import base64
import csv
import itertools
import json
import mimetypes
import operator
from copy import copy
from datetime import date, datetime, timezone
from datetime import timedelta
from decimal import Decimal
from functools import reduce
from urllib.parse import parse_qs, urlencode

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.db.models import (
    Q,
    ExpressionWrapper,
    Sum,
    Case,
    F,
    When,
    Subquery,
    OuterRef,
    Count,
    Max,
)
from django.db.models.functions import TruncMonth, Coalesce
from django.forms import CheckboxInput
from django.forms.widgets import Select
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.views.generic import View
from django_filters import ChoiceFilter, Filter
from django_filters import (
    FilterSet,
    CharFilter,
    OrderingFilter,
    ModelChoiceFilter,
    BooleanFilter,
)
from django_filters.views import FilterView

from tapir import settings
from tapir.accounts.models import EmailChangeRequest, TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import (
    ProductTypes,
    Permission,
)
from tapir.wirgarten.forms.member.forms import (
    PaymentAmountEditForm,
    CoopShareTransferForm,
    PersonalDataForm,
    WaitingListForm,
    TrialCancellationForm,
    SubscriptionRenewalForm,
    CoopShareCancelForm,
)
from tapir.wirgarten.forms.pickup_location import (
    PickupLocationChoiceForm,
    get_pickup_locations_map_data,
)
from tapir.wirgarten.forms.registration import HarvestShareForm
from tapir.wirgarten.forms.registration.bestellcoop import BestellCoopForm
from tapir.wirgarten.forms.registration.chicken_shares import ChickenShareForm
from tapir.wirgarten.forms.registration.coop_shares import CooperativeShareForm
from tapir.wirgarten.forms.registration.payment_data import PaymentDataForm
from tapir.wirgarten.models import (
    Member,
    Subscription,
    Payment,
    Deliveries,
    GrowingPeriod,
    EditFuturePaymentLogEntry,
    MandateReference,
    WaitingListEntry,
    PickupLocationCapability,
    PickupLocation,
    ProductType,
    Product,
    CoopShareTransaction,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
    get_active_pickup_locations,
    generate_future_deliveries,
)
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.service.file_export import begin_csv_string
from tapir.wirgarten.service.member import (
    transfer_coop_shares,
    create_wait_list_entry,
    buy_cooperative_shares,
    get_subscriptions_in_trial_period,
    get_next_contract_start_date,
    send_order_confirmation,
    cancel_coop_shares,
)
from tapir.wirgarten.service.payment import (
    get_next_payment_date,
    is_mandate_ref_for_coop_shares,
    get_active_subscriptions_grouped_by_product_type,
)
from tapir.wirgarten.service.products import (
    get_total_price_for_subs,
    get_product_price,
    get_active_product_types,
    is_harvest_shares_available,
    get_future_subscriptions,
    is_chicken_shares_available,
    is_bestellcoop_available,
    get_next_growing_period,
    product_type_order_by,
    get_active_subscriptions,
)
from tapir.wirgarten.utils import format_date, format_currency
from tapir.wirgarten.views.mixin import PermissionOrSelfRequiredMixin
from tapir.wirgarten.views.modal import get_form_modal


# FIXME: this file needs some serious refactoring. Some of the functions should either be generalized service functions or private functions.


class MultiFieldFilter(Filter):
    def __init__(self, fields=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields = fields or []

    def filter(self, qs, value):
        if value:
            lookups = [Q(**{f"{field}__icontains": value}) for field in self.fields]
            qs = qs.filter(reduce(operator.or_, lookups))
        return qs


class ContractStatusFilter(ChoiceFilter):
    def filter(self, qs, value):
        # Filter members with an active subscription which is not cancelled
        if value:
            today = date.today()
            qs = qs.filter(
                subscription__start_date__lte=today,
                subscription__end_date__gte=today,
            )

        if value == "Contract Renewed":
            # Get the upcoming growing period
            growing_period = get_next_growing_period()

            # Filter members with at least one subscription starting in the upcoming growing period
            qs = qs.filter(
                subscription__start_date__gte=growing_period.start_date,
                subscription__start_date__lte=growing_period.end_date,
            )

        elif value == "Contract Cancelled":
            trial_period_end = ExpressionWrapper(
                TruncMonth(F("subscription__start_date"))
                + timedelta(
                    days=relativedelta(months=1).days,
                    seconds=relativedelta(months=1).seconds,
                ),
                output_field=models.DateField(),
            )

            qs = qs.annotate(trial_period_end=trial_period_end).filter(
                subscription__cancellation_ts__gt=F("trial_period_end"),
                subscription__cancellation_ts__isnull=False,
            )

        elif value == "Undecided":
            growing_period = get_next_growing_period()

            # Calculate the trial period start date
            trial_period_start = date.today() + relativedelta(months=-1, day=1)

            # Filter members with no active subscriptions that started within the last month
            qs = qs.filter(subscription__start_date__lte=trial_period_start).exclude(
                subscription__cancellation_ts__isnull=False,
            )

            qs = qs.exclude(
                subscription__start_date__gte=growing_period.start_date,
                subscription__start_date__lte=growing_period.end_date,
            )

        return qs.distinct()


class MemberFilter(FilterSet):
    search = MultiFieldFilter(
        fields=["first_name", "last_name", "email"], label="Suche"
    )
    pickup_location = ModelChoiceFilter(
        queryset=PickupLocation.objects.all().order_by("name"),
        field_name="pickup_location__name",
        label="Abholort",
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
    no_coop_shares = BooleanFilter(
        label="Keine Geno-Anteile",
        method="filter_no_coop_shares",
        widget=CheckboxInput(),
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
            ("created_at", "⮝ Registriert am"),
            ("coop_shares_total_value", "⮝ Genoanteile"),
            ("-coop_shares_total_value", "⮟ Genoanteile"),
            ("monthly_payment", "⮝ Umsatz"),
            ("-monthly_payment", "⮟ Umsatz"),
        ),
        required=True,
        empty_label=None,
    )

    def filter_email_verified(self, queryset, name, value):
        new_queryset = queryset.all()
        for member in queryset:
            if member.email_verified() != value:
                new_queryset = new_queryset.exclude(id=member.id)
        return new_queryset

    def filter_no_coop_shares(self, queryset, name, value):
        if value:
            return queryset.filter(coop_shares_total_value__lte=0)
        else:
            return queryset.filter(coop_shares_total_value__gt=0)

    def __init__(self, data=None, *args, **kwargs):
        if data is None:
            data = {"o": "-created_at"}
        else:
            data = data.copy()

            if "o" not in data:
                data["o"] = "-created_at"

        super(MemberFilter, self).__init__(data, *args, **kwargs)


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
        today = date.today()
        overnext_month = today + relativedelta(months=2)

        return Member.objects.annotate(
            coop_shares_total_value=Coalesce(
                Subquery(
                    CoopShareTransaction.objects.filter(
                        member_id=OuterRef("id"),
                        valid_at__lte=overnext_month,
                        # I do this to include new members in the list, which will join the coop soon
                    )
                    .values("member_id")
                    .annotate(total_value=Sum(F("quantity") * F("share_price")))
                    .values("total_value"),
                    output_field=models.DecimalField(),
                ),
                Decimal(0.0),
            ),
            monthly_payment=Sum(
                Case(
                    When(
                        Q(subscription__start_date__lte=today)
                        & Q(subscription__end_date__gte=today)
                        & Q(subscription__product__productprice__valid_from__lte=today),
                        then=F("subscription__product__productprice__price")
                        * F("subscription__quantity")
                        * (1 + F("subscription__solidarity_price")),
                    ),
                    default=0.0,
                    output_field=models.FloatField(),
                )
            ),
        )


class MemberDetailView(PermissionOrSelfRequiredMixin, generic.DetailView):
    model = Member
    template_name = "wirgarten/member/member_detail.html"
    permission_required = Permission.Accounts.VIEW

    def get_user_pk(self):
        return self.kwargs["pk"]

    def get_context_data(self, **kwargs):
        context = super(MemberDetailView, self).get_context_data()

        today = kwargs.get("start_date", date.today())
        next_month = today + relativedelta(months=1, day=1)

        context["object"] = self.object
        context["subscriptions"] = get_active_subscriptions_grouped_by_product_type(
            self.object, today
        )

        context["sub_quantities"] = {
            k: sum(map(lambda x: x.quantity, v))
            for k, v in context["subscriptions"].items()
        }
        context["sub_totals"] = {
            k: sum(map(lambda x: x.total_price, v))
            for k, v in context["subscriptions"].items()
        }

        product_types = get_active_product_types()
        for pt in product_types:
            if pt.name not in context["subscriptions"]:
                context["subscriptions"][pt.name] = []
                context["sub_quantities"][pt.name] = 0

        share_ownerships = list(
            CoopShareTransaction.objects.filter(member=self.object).order_by(
                "timestamp"
            )
        )
        context["coop_shares"] = share_ownerships

        context["coop_shares_total"] = self.object.coop_shares_quantity

        additional_products_available = self.object.coop_entry_date is not None and (
            get_future_subscriptions()
            .filter(
                member_id=self.object.id,
                end_date__gt=get_next_contract_start_date(),
                product__type_id=get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE),
            )
            .exists()
        )

        context["available_product_types"] = {
            ProductTypes.HARVEST_SHARES: is_harvest_shares_available(next_month),
            ProductTypes.CHICKEN_SHARES: additional_products_available
            and is_chicken_shares_available(next_month),
            ProductTypes.BESTELLCOOP: additional_products_available
            and (
                not (
                    len(context["subscriptions"][ProductTypes.BESTELLCOOP]) > 0
                    and context["subscriptions"][ProductTypes.BESTELLCOOP][0].quantity
                    > 0
                )
                or context["subscriptions"][ProductTypes.BESTELLCOOP][0].cancellation_ts
                is not None
            )
            and is_bestellcoop_available(next_month),
        }

        if self.object.pickup_location:
            context["pickup_location_map_data"] = get_pickup_locations_map_data(
                [self.object.pickup_location],
                PickupLocationCapability.objects.filter(
                    pickup_location=self.object.pickup_location
                ),
            )
        else:
            capabilities = get_active_pickup_location_capabilities()
            context["pickup_location_map_data"] = get_pickup_locations_map_data(
                get_active_pickup_locations(capabilities), capabilities
            )

        context["deliveries"] = generate_future_deliveries(self.object)

        # FIXME: it should be easier than this to get the next payments, refactor to service somehow
        prev_payments = get_previous_payments(self.object.pk)
        now = date.today()
        for payment in prev_payments:
            if payment["due_date"] >= now:
                context["next_payment"] = payment
            else:
                break

        next_payments = generate_future_payments(self.object.id, prev_payments, 1)

        if len(next_payments) > 0:
            if "next_payment" not in context or (
                next_payments[0]["due_date"] < context["next_payment"]["due_date"]
            ):
                context["next_payment"] = next_payments[0]

        self.add_renewal_notice_context(context, next_month, today)

        subs_in_trial = get_subscriptions_in_trial_period(self.object.id)
        if subs_in_trial.exists():
            context["show_trial_period_notice"] = True
            context["subscriptions_in_trial"] = subs_in_trial
            context["next_trial_end_date"] = min(
                subs_in_trial, key=lambda x: x.start_date
            ).start_date + relativedelta(day=1, months=1, days=-1)
        elif (
            self.object.coop_entry_date is not None
            and self.object.coop_entry_date > today
            and self.object.coopsharetransaction_set.aggregate(
                quantity=Sum(F("quantity"))
            )["quantity"]
            > 0
        ):
            context["show_trial_period_notice"] = True
            context["subscriptions_in_trial"] = [
                "Beitrittserklärung zur Genossenschaft"
            ]
            context["next_trial_end_date"] = share_ownerships[
                0
            ].valid_at + relativedelta(days=-1)

        email_change_requests = EmailChangeRequest.objects.filter(
            user_id=self.object.id
        )
        if email_change_requests.exists():
            context["email_change_request"] = {
                "new_email": email_change_requests[0].new_email
            }

        return context

    def add_renewal_notice_context(self, context, next_month, today):
        """
        Renewal notice:
         - show_renewal_warning = less than 3 months before next period starts
         - add_shares_disallowed = less than 1 month
         - renewal_status = "unknown", "renewed", "cancelled"
        """
        if not get_active_subscriptions().filter(member_id=self.object.id).exists():
            return

        next_growing_period = get_next_growing_period(today)
        if (
            next_growing_period
            and (today + relativedelta(months=3)) > next_growing_period.start_date
        ):
            context["next_period"] = next_growing_period
            context["add_shares_disallowed"] = (
                next_month >= next_growing_period.start_date
            )  # 1 month before

            harvest_share_subs = context["subscriptions"][ProductTypes.HARVEST_SHARES]

            if len(harvest_share_subs) < 1:
                context["show_renewal_warning"] = False
                return  # no harvest share subs, nothing to renew. Member can add subscriptions via the "+" button
            else:
                context["show_renewal_warning"] = True

            context["contract_end_date"] = contract_end_date = (
                format_date(harvest_share_subs[0].end_date)
                if type(harvest_share_subs[0]) is Subscription
                else None
            )
            cancelled = any(
                map(
                    lambda x: (None if type(x) is dict else x.cancellation_ts)
                    is not None,
                    harvest_share_subs,
                )
            )
            future_subs = get_future_subscriptions(
                next_growing_period.start_date
            ).filter(member_id=self.object.id, cancellation_ts__isnull=True)
            has_future_subs = future_subs.exists()
            if cancelled and not has_future_subs:
                context[
                    "renewal_status"
                ] = "cancelled"  # --> show cancellation confirmation
            elif has_future_subs:
                context["renewal_status"] = "renewed"  # --> show renewal confirmation
            else:
                if context["available_product_types"][ProductTypes.HARVEST_SHARES]:
                    context["renewal_status"] = "unknown"  # --> show renewal notice
                elif WaitingListEntry.objects.filter(
                    email=self.object.email,
                    type=WaitingListEntry.WaitingListType.HARVEST_SHARES,
                ).exists():
                    context[
                        "renewal_status"
                    ] = "waitlist"  # --> show waitlist confirmation
                else:
                    context["renewal_status"] = "no_capacity"  # --> show waitlist

            context["renewal_alert"] = {
                "unknown": {
                    "header": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_UNKOWN_HEADER,
                        contract_end_date,
                        next_growing_period,
                    ),
                    "content": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_UNKOWN_CONTENT,
                        contract_end_date,
                        next_growing_period,
                    ),
                },
                "cancelled": {
                    "header": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_CANCELLED_HEADER,
                        contract_end_date,
                        next_growing_period,
                    ),
                    "content": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_CANCELLED_CONTENT,
                        contract_end_date,
                        next_growing_period,
                    ),
                },
                "renewed": {
                    "header": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_RENEWED_HEADER,
                        contract_end_date,
                        next_growing_period,
                    ),
                    "content": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_RENEWED_CONTENT,
                        contract_end_date,
                        next_growing_period,
                        contract_list=f"{'<br/>'.join(map(lambda x: '- ' + str(x), future_subs))}<br/>",
                    ),
                },
                "no_capacity": {
                    "header": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_WAITLIST_HEADER,
                        contract_end_date,
                        next_growing_period,
                    ),
                    "content": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_WAITLIST_CONTENT,
                        contract_end_date,
                        next_growing_period,
                    ),
                },
            }

    def format_param(
        self,
        key: str,
        contract_end_date: str,
        next_growing_period: GrowingPeriod,
        **kwargs,
    ):
        return get_parameter_value(key).format(
            member=self.object,
            contract_end_date=contract_end_date,
            next_period_start_date=format_date(next_growing_period.start_date),
            next_period_end_date=format_date(next_growing_period.end_date),
            **kwargs,
        )


@require_http_methods(["GET"])
@csrf_protect
@login_required
@transaction.atomic
def renew_contract_same_conditions(request, **kwargs):
    member_id = kwargs["pk"]
    new_subs = []
    next_period = get_next_growing_period()

    available_product_types = {
        ProductTypes.HARVEST_SHARES: is_harvest_shares_available(
            next_period.start_date
        ),
        ProductTypes.CHICKEN_SHARES: is_chicken_shares_available(
            next_period.start_date
        ),
        ProductTypes.BESTELLCOOP: is_bestellcoop_available(next_period.start_date),
    }

    for sub in get_active_subscriptions().filter(member_id=member_id):
        if available_product_types[sub.product.type.name]:
            new_subs.append(
                Subscription(
                    member=sub.member,
                    product=sub.product,
                    period=next_period,
                    quantity=sub.quantity,
                    start_date=next_period.start_date,
                    end_date=next_period.end_date,
                    solidarity_price=sub.solidarity_price,
                    mandate_ref=sub.mandate_ref,
                )
            )
            # reset cancellation date on existing sub
            sub.cancellation_ts = None
            sub.save()
        else:
            print(
                f"[{sub.member.id}] Renew with same conditions. Skipping {sub.product.type.name} because there is no capacity or the product type was removed."
            )

    Subscription.objects.bulk_create(new_subs)
    send_order_confirmation(Member.objects.get(id=member_id), new_subs)

    return HttpResponseRedirect(member_detail_url(member_id))


@require_http_methods(["GET"])
@csrf_protect
@login_required
@transaction.atomic
def cancel_contract_at_period_end(request, **kwargs):
    member_id = kwargs["pk"]
    # if not member_id == request.user.pk:
    #    raise PermissionDenied("A member can only cancel a contract themself.")

    now = timezone.now()
    subs = list(get_future_subscriptions().filter(member_id=member_id))
    for sub in subs:
        sub.cancellation_ts = now
        sub.save()

    end_date = subs[0].end_date

    member = Member.objects.get(id=member_id)
    send_email(
        to_email=[member.email],
        subject=get_parameter_value(Parameter.EMAIL_NOT_RENEWED_CONFIRMATION_SUBJECT),
        content=get_parameter_value(Parameter.EMAIL_NOT_RENEWED_CONFIRMATION_CONTENT),
    )

    return HttpResponseRedirect(
        member_detail_url(member_id) + "?notrenewed=" + format_date(end_date)
    )


def generate_future_payments(member_id, prev_payments: list, limit: int = None):
    prev_payments = set(map(lambda p: (p["mandate_ref"], p["due_date"]), prev_payments))
    subs = get_future_subscriptions().filter(member_id=member_id)

    payments = []
    next_payment_date = get_next_payment_date()
    last_growing_period = GrowingPeriod.objects.order_by("-end_date")[:1][0]
    while next_payment_date <= last_growing_period.end_date and (
        limit is None or len(payments) < limit
    ):
        active_subs = subs.filter(
            start_date__lte=next_payment_date, end_date__gte=next_payment_date
        )
        if active_subs.count() > 0:

            groups = itertools.groupby(active_subs, lambda v: v.mandate_ref)

            for mandate_ref, values in groups:
                values = list(values)
                due_date = next_payment_date

                if (mandate_ref, due_date) not in prev_payments:
                    amount = get_total_price_for_subs(values)
                    payments.append(
                        {
                            "due_date": due_date,
                            "mandate_ref": mandate_ref,
                            "amount": amount,
                            "calculated_amount": amount,
                            "subs": list(map(sub_to_dict, active_subs)),
                            "status": Payment.PaymentStatus.DUE,
                            "edited": False,
                            "upcoming": True,
                        }
                    )

        next_payment_date += relativedelta(months=1)

    return payments


def get_subs_or_shares_for_mandate_ref(
    mandate_ref: MandateReference, reference_date: date
):
    if is_mandate_ref_for_coop_shares(mandate_ref):
        return list(
            map(
                lambda x: {
                    "quantity": x.quantity,
                    "product": {
                        "name": _("Genossenschaftsanteile"),
                        "price": x.share_price,
                    },
                    "total_price": x.total_price,
                },
                CoopShareTransaction.objects.filter(member_id=mandate_ref.member.id),
            )
        )
    else:
        return list(
            map(
                lambda x: sub_to_dict(x),
                Subscription.objects.filter(
                    mandate_ref=mandate_ref,
                    start_date__lte=reference_date,
                    end_date__gt=reference_date,
                ),
            )
        )


def sub_to_dict(sub):
    if type(sub) is dict:
        return sub

    price = get_product_price(sub.product, sub.start_date).price
    return {
        "quantity": sub.quantity,
        "product": {
            "name": sub.product.name,
            "type": {"name": sub.product.type.name},
            "price": price,
        },
        "solidarity_price": sub.solidarity_price,
        "total_price": sub.total_price,
    }


def payment_to_dict(payment: Payment) -> dict:
    subs = get_subs_or_shares_for_mandate_ref(payment.mandate_ref, payment.due_date)
    return {
        "due_date": payment.due_date,
        "mandate_ref": payment.mandate_ref,
        "amount": float(round(payment.amount, 2)),
        "calculated_amount": round(sum(map(lambda x: x["total_price"], subs)), 2),
        "subs": list(map(sub_to_dict, subs)),
        "status": payment.status,
        "edited": payment.edited,
        "upcoming": (date.today() - payment.due_date).days < 0,
    }


def get_previous_payments(member_id) -> [dict]:
    return list(
        map(
            lambda x: payment_to_dict(x),
            Payment.objects.filter(mandate_ref__member_id=member_id).order_by(
                "-due_date"
            ),
        )
    )


class MemberPaymentsView(
    PermissionOrSelfRequiredMixin, generic.TemplateView, generic.base.ContextMixin
):
    template_name = "wirgarten/member/member_payments.html"
    permission_required = Permission.Payments.VIEW

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_id = kwargs["pk"]

        context["payments"] = self.get_payments_row(member_id)
        context["member"] = Member.objects.get(pk=member_id)

        return context

    def get_payments_row(self, member_id):
        prev_payments = get_previous_payments(member_id)
        future_payments = generate_future_payments(member_id, prev_payments)

        return sorted(
            prev_payments + future_payments,
            key=lambda x: x["due_date"].isoformat() + x["mandate_ref"].ref,
        )


def get_previous_deliveries(member: Member):
    return list(
        map(
            lambda x: {
                "pickup_location": x.pickup_location,
                "delivery_date": x.delivery_date,
                "subs": Subscription.objects.filter(
                    member=x.member,
                    start_date__lte=x.due_date,
                    end_date__gt=x.due_date,
                ),
            },
            Deliveries.objects.filter(member=member),
        )
    )


class MemberDeliveriesView(
    PermissionOrSelfRequiredMixin, generic.TemplateView, generic.base.ContextMixin
):
    template_name = "wirgarten/member/member_deliveries.html"
    permission_required = Permission.Accounts.VIEW

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_id = kwargs["pk"]

        member = Member.objects.get(pk=member_id)

        context["member"] = member
        context["deliveries"] = get_previous_deliveries(
            member
        ) + generate_future_deliveries(member)

        return context


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Payments.MANAGE)
@csrf_protect
def get_payment_amount_edit_form(request, **kwargs):
    @transaction.atomic
    def save_future_payment_change():
        def create_payment_edit_logentry(new_payment):
            member = Member.objects.get(pk=kwargs["member_id"])
            comment = form.data["comment"]
            if hasattr(form, "payment"):
                EditFuturePaymentLogEntry().populate(
                    old_model=form.payment,
                    new_model=new_payment,
                    actor=request.user,
                    user=member,
                    comment=comment,
                ).save()
            else:
                EditFuturePaymentLogEntry().populate(
                    old_frozen={},
                    new_model=new_payment,
                    actor=request.user,
                    user=member,
                    comment=comment,
                ).save()

        if not hasattr(form, "payment"):
            new_payment = Payment.objects.create(
                due_date=form.payment_due_date,
                amount=form.data["amount"],
                mandate_ref_id=form.mandate_ref_id,
                edited=True,
            )
        else:
            new_payment = copy(form.payment)
            new_payment.amount = form.data["amount"]
            new_payment.edited = True
            new_payment.save()

        create_payment_edit_logentry(new_payment)

    if request.method == "POST":
        form = PaymentAmountEditForm(request.POST, **kwargs)
        if form.is_valid():
            save_future_payment_change()

            return HttpResponseRedirect(
                reverse_lazy(
                    "wirgarten:member_payments",
                    kwargs={"pk": kwargs["member_id"]},
                    current_app="wirgarten",
                )
            )

    else:
        form = PaymentAmountEditForm(**kwargs)
        return render(
            request, "wirgarten/member/member_payments_edit_form.html", {"form": form}
        )


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def get_coop_share_transfer_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=CoopShareTransferForm,
        handler=lambda x: transfer_coop_shares(
            origin_member_id=kwargs["pk"],
            target_member_id=x.cleaned_data["receiver"],
            quantity=x.cleaned_data["quantity"],
            actor=request.user,
        ),
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:member_list"),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def get_coop_share_cancel_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=CoopShareCancelForm,
        handler=lambda x: cancel_coop_shares(
            member=kwargs["pk"],
            quantity=x.cleaned_data["quantity"],
            cancellation_date=x.cleaned_data["cancellation_date"],
            valid_at=x.cleaned_data["valid_at"],
        ),
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:member_list"),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@csrf_protect
@login_required
def get_member_personal_data_edit_form(request, **kwargs):
    pk = kwargs.pop("pk")

    check_permission_or_self(pk, request)

    kwargs["can_edit_name_and_birthdate"] = request.user.has_perm(
        Permission.Accounts.MANAGE
    )
    kwargs["can_edit_email"] = not get_parameter_value(Parameter.MEMBER_LOCK_FUNCTIONS)

    return get_form_modal(
        request=request,
        form=PersonalDataForm,
        instance=Member.objects.get(pk=pk),
        handler=lambda x: x.instance.save(),
        redirect_url_resolver=lambda _: member_detail_url(pk),
        **kwargs,
    )


def member_detail_url(member_id):
    return reverse_lazy("wirgarten:member_detail", kwargs={"pk": member_id})


def check_permission_or_self(pk, request):
    if not (request.user.pk == pk or request.user.has_perm(Permission.Accounts.MANAGE)):
        raise PermissionDenied


@require_http_methods(["GET", "POST"])
@csrf_protect
@login_required
def get_member_payment_data_edit_form(request, **kwargs):
    member_id = kwargs.pop("pk")
    check_permission_or_self(member_id, request)

    instance = Member.objects.get(pk=member_id)

    def update_payment_data(member: Member, account_owner: str, iban: str, bic: str):
        member.account_owner = account_owner
        member.iban = iban
        member.bic = bic
        member.sepa_consent = timezone.now()
        member.save()
        return member

    return get_form_modal(
        request=request,
        form=PaymentDataForm,
        instance=instance,
        handler=lambda x: update_payment_data(
            member=instance,
            account_owner=x.cleaned_data["account_owner"],
            iban=x.cleaned_data["iban"],
            bic=x.cleaned_data["bic"],
        ),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@csrf_protect
@login_required
def get_pickup_location_choice_form(request, **kwargs):
    member_id = kwargs.pop("pk")
    check_permission_or_self(member_id, request)

    member = Member.objects.get(pk=member_id)
    kwargs["initial"] = {
        "product_types": get_active_subscriptions_grouped_by_product_type(
            member
        ).keys(),
    }
    if member.pickup_location:
        kwargs["initial"]["initial"] = member.pickup_location.id

    def update_pickup_location(pickup_location_id):
        member.pickup_location_id = pickup_location_id
        member.save()

    return get_form_modal(
        request=request,
        form=PickupLocationChoiceForm,
        handler=lambda x: update_pickup_location(x.cleaned_data["pickup_location"]),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Accounts.MANAGE)
@csrf_protect
def get_member_personal_data_create_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=PersonalDataForm,
        handler=lambda x: x.instance.save(),
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:member_list"),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_harvest_shares_waiting_list_form(request, **kwargs):
    if request.user and Member.objects.filter(id=request.user.id).exists():
        kwargs["initial"] = {
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
        }
        kwargs["redirect_url_resolver"] = lambda _: member_detail_url(request.user.id)

    return get_form_modal(
        request=request,
        form=WaitingListForm,
        handler=lambda x: create_wait_list_entry(
            first_name=x.cleaned_data["first_name"],
            last_name=x.cleaned_data["last_name"],
            email=x.cleaned_data["email"],
            type=WaitingListEntry.WaitingListType.HARVEST_SHARES,
        ),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_coop_shares_waiting_list_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=WaitingListForm,
        handler=lambda x: create_wait_list_entry(
            first_name=x.cleaned_data["first_name"],
            last_name=x.cleaned_data["last_name"],
            email=x.cleaned_data["email"],
            type=WaitingListEntry.WaitingListType.COOP_SHARES,
        ),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_renew_contracts_form(request, **kwargs):
    member_id = kwargs.pop("pk")
    check_permission_or_self(member_id, request)

    kwargs["start_date"] = get_next_growing_period().start_date

    return get_form_modal(
        request=request,
        form=SubscriptionRenewalForm,
        handler=lambda x: x.save(
            member_id=member_id,
        ),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_add_harvest_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    check_permission_or_self(member_id, request)

    if not is_harvest_shares_available():
        # FIXME: better don't even show the form to a member, just one button to be added to the waitlist
        member = Member.objects.get(pk=member_id)
        wl_kwargs = kwargs.copy()
        wl_kwargs["initial"] = {
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "privacy_consent": (member.privacy_consent is not None),
        }
        return get_harvest_shares_waiting_list_form(request, **wl_kwargs)

    return get_form_modal(
        request=request,
        form=HarvestShareForm,
        handler=lambda x: x.save(member_id=member_id, send_email=True),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_add_chicken_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    check_permission_or_self(member_id, request)

    if not is_chicken_shares_available():
        raise Exception("Keine Hühneranteile verfügbar")

    return get_form_modal(
        request=request,
        form=ChickenShareForm,
        handler=lambda x: x.save(
            member_id=member_id,
        ),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_add_bestellcoop_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    check_permission_or_self(member_id, request)

    if not is_bestellcoop_available():
        raise Exception("BestellCoop nicht verfügbar")

    return get_form_modal(
        request=request,
        form=BestellCoopForm,
        handler=lambda x: x.save(
            member_id=member_id,
        ),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_add_coop_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    check_permission_or_self(member_id, request)

    if not get_parameter_value(Parameter.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES):
        # FIXME: better don't even show the form to a member, just one button to be added to the waitlist
        member = Member.objects.get(pk=member_id)
        wl_kwargs = kwargs.copy()
        wl_kwargs["initial"] = {
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "privacy_consent": (member.privacy_consent is not None),
        }
        return get_coop_shares_waiting_list_form(request, **wl_kwargs)

    today = date.today()
    return get_form_modal(
        request=request,
        form=CooperativeShareForm,
        handler=lambda x: buy_cooperative_shares(
            x.cleaned_data["cooperative_shares"], member_id, start_date=today
        ),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_cancel_trial_form(request, **kwargs):
    member_id = kwargs["pk"]
    check_permission_or_self(member_id, request)

    return get_form_modal(
        request=request,
        form=TrialCancellationForm,
        handler=lambda x: x.save(),
        redirect_url_resolver=lambda x: member_detail_url(member_id)
        + "?cancelled="
        + format_date(x),
        **kwargs,
    )


class WaitingListFilter(FilterSet):
    type = ChoiceFilter(
        label=_("Warteliste"),
        lookup_expr="exact",
        choices=WaitingListEntry.WaitingListType.choices,
        empty_label=None,
        initial=0,
    )
    first_name = CharFilter(label=_("Vorname"), lookup_expr="icontains")
    last_name = CharFilter(label=_("Nachname"), lookup_expr="icontains")
    email = CharFilter(label=_("Email"), lookup_expr="icontains")

    def __init__(self, data=None, *args, **kwargs):
        if data is None:
            data = {"type": WaitingListEntry.WaitingListType.HARVEST_SHARES}
        else:
            data = data.copy()

            if not data["type"]:
                data["type"] = WaitingListEntry.WaitingListType.HARVEST_SHARES

        super().__init__(data, *args, **kwargs)

    class Meta:
        model = WaitingListEntry
        fields = ["type", "first_name", "last_name", "email"]


class WaitingListView(PermissionRequiredMixin, FilterView):
    filterset_class = WaitingListFilter
    ordering = ["created_at"]
    permission_required = Permission.Accounts.MANAGE
    template_name = "wirgarten/waitlist/waitlist_filter.html"
    paginated_by = 20


@require_GET
@csrf_protect
@permission_required(Permission.Coop.MANAGE)
def export_waitinglist(request, **kwargs):
    waitlist_type = request.environ["QUERY_STRING"].replace("type=", "")
    if not waitlist_type:
        return  # unknown waitlist type, can never happen from UI

    waitlist_type_label = list(
        filter(
            lambda x: x[0] == waitlist_type, WaitingListEntry.WaitingListType.choices
        )
    )[0][1]

    KEY_FIRST_NAME = "Vorname"
    KEY_LAST_NAME = "Nachname"
    KEY_EMAIL = "Email"
    KEY_SINCE = "Wartet seit"

    output, writer = begin_csv_string(
        [KEY_FIRST_NAME, KEY_LAST_NAME, KEY_EMAIL, KEY_SINCE]
    )
    for entry in WaitingListEntry.objects.filter(type=waitlist_type):
        writer.writerow(
            {
                KEY_FIRST_NAME: entry.first_name,
                KEY_LAST_NAME: entry.last_name,
                KEY_EMAIL: entry.email,
                KEY_SINCE: entry.created_at,
            }
        )

    filename = f"Warteliste-{waitlist_type_label}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    mime_type, _ = mimetypes.guess_type(filename)
    response = HttpResponse("".join(output.csv_string), content_type=mime_type)
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response


class SecondaryOrderingFilter(OrderingFilter):
    def __init__(self, *args, secondary_ordering="id", **kwargs):
        self.secondary_ordering = secondary_ordering
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            ordering_fields = [self.get_ordering_value(v) for v in value] + [
                f"{'-' if value[0][0] == '-' else ''}{self.secondary_ordering}"
            ]
        else:
            ordering_fields = ["-created_at", f"-{self.secondary_ordering}"]

        return qs.order_by(*ordering_fields)


class SubscriptionListFilter(FilterSet):
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
    member__pickup_location = ModelChoiceFilter(
        label=_("Abholort"), queryset=PickupLocation.objects.all().order_by("name")
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

    class Meta:
        model = Subscription
        fields = []

    def __init__(self, data=None, *args, **kwargs):
        def get_default_period_filter_value():
            today = date.today()
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
            min_start_date = date.today() + relativedelta(day=1, months=-1)
            return queryset.filter(start_date__gt=min_start_date, cancellation_ts=None)
        return queryset


class SubscriptionListView(PermissionRequiredMixin, FilterView):
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
        context["today"] = date.today()
        context["total_contracts"] = self.filterset.qs.aggregate(
            total_count=Sum("quantity")
        )["total_count"]
        return context


EMAIL_CHANGE_LINK_VALIDITY_MINUTES = 4 * 60


@transaction.atomic
def change_email(request, **kwargs):
    data = json.loads(base64.b64decode(kwargs["token"]))
    user_id = data["user"]
    new_email = data["new_email"]
    matching_change_request = EmailChangeRequest.objects.filter(
        new_email=new_email, secret=data["secret"], user_id=user_id
    ).order_by("-created_at")

    link_validity = relativedelta(minutes=EMAIL_CHANGE_LINK_VALIDITY_MINUTES)
    now = datetime.now(tz=timezone.utc)
    if matching_change_request.exists() and now < (
        matching_change_request[0].created_at + link_validity
    ):
        # token is valid -> actually change email
        user = TapirUser.objects.get(id=user_id)
        orig_email = user.email
        user.change_email(new_email)

        # delete other change requests for this user
        EmailChangeRequest.objects.filter(user_id=user_id).delete()
        # delete expired change requests
        EmailChangeRequest.objects.filter(created_at__lte=now - link_validity).delete()

        # send confirmation to old email address
        send_email(
            to_email=[orig_email],
            subject=_("Deine Email Adresse wurde geändert"),
            content=_(
                f"Hallo {user.first_name},<br/><br/>"
                f"deine Email Adresse wurde erfolgreich zu <strong>{new_email}</strong> geändert.<br/>"
                f"""Falls du das nicht warst, ändere bitte sofort dein Passwort im <a href="{settings.SITE_URL}" target="_blank">Mitgliederbereich</a> und kontaktiere uns indem du einfach auf diese Mail antwortest."""
                f"<br/><br/>Herzliche Grüße, dein WirGarten Team"
            ),
        )

        return HttpResponseRedirect(
            reverse_lazy("wirgarten:member_detail", kwargs={"pk": user.id})
            + "?email_changed=true"
        )

    return HttpResponseRedirect(reverse_lazy("link_expired"))


@require_http_methods(["GET"])
@permission_required(Permission.Accounts.MANAGE)
@csrf_protect
def resend_verify_email(request, **kwargs):
    member_id = kwargs["pk"]
    member = Member.objects.get(id=member_id)
    try:
        member.send_verify_email()
        result = "success"
    except Exception as e:
        result = str(e)

    next_url = request.environ["QUERY_STRING"].replace("next=", "")

    return HttpResponseRedirect(next_url + "&resend_verify_email=" + result)


class ExportMembersView(View):
    def get(self, request, *args, **kwargs):
        # Get queryset based on filters and ordering
        filter_class = MemberFilter
        queryset = filter_class(request.GET, queryset=self.get_queryset()).qs

        # Create response object with CSV content
        response = HttpResponse(content_type="text/csv")
        response[
            "Content-Disposition"
        ] = f'attachment; filename="Mitglieder_gefiltert_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        writer = csv.writer(response, delimiter=";")

        # Write header row
        writer.writerow(
            [
                "#",
                "Vorname",
                "Nachname",
                "Email",
                "Telefon",
                "Adresse",
                "PLZ",
                "Ort",
                "Land",
                "Registriert am",
                "Geno-Beitritt am",
                "Geschäftsanteile (€)",
                "Umsatz/Monat (€)",
                "Abholort",
            ]
        )

        # Write data rows
        for member in queryset:
            writer.writerow(
                [
                    member.member_no,
                    member.first_name,
                    member.last_name,
                    member.email,
                    member.phone_number,
                    member.street + (", " + member.street_2) if member.street_2 else "",
                    member.postcode,
                    member.city,
                    member.country,
                    format_date(member.created_at.date()),
                    format_date(member.coop_entry_date),
                    format_currency(member.coop_shares_total_value),
                    format_currency(member.monthly_payment),
                    member.pickup_location.name if member.pickup_location else "",
                ]
            )

        return response

    def get_queryset(self):
        return MemberListView.get_queryset(self)

    def get_filterset_class(self):
        return MemberFilter

    def get_success_url(self):
        return reverse_lazy("member_list")


@require_GET
@csrf_protect
@permission_required(Permission.Coop.VIEW)
def export_coop_member_list(request, **kwargs):
    KEY_MEMBER_NO = "Nr"
    KEY_FIRST_NAME = "Vorname"
    KEY_LAST_NAME = "Nachname"
    KEY_ADDRESS = "Straße + Hausnr."
    KEY_ADDRESS2 = "Adresse 2"
    KEY_POSTCODE = "PLZ"
    KEY_CITY = "Ort"
    KEY_BIRTHDATE = "Geburtstag/Gründungsdatum"
    KEY_TELEPHONE = "Telefon"
    KEY_EMAIL = "Mailadresse"
    KEY_COOP_SHARES_TOTAL = "GAnteile gesamt"
    KEY_COOP_SHARES_TOTAL_EURO = "GAnteile in € gesamt"
    KEY_COOP_SHARES_CANCELLATION_DATE = (
        "Kündigungsdatum der Mitgliedschaft/ (einzelner) Geschäftsanteile"
    )
    KEY_COOP_SHARES_CANCELLATION_AMOUNT = "Wert der gekündigten Geschäftsanteile"
    KEY_COOP_SHARES_CANCELLATION_CONTRACT_END_DATE = (
        "Inkrafttreten der Kündigung der Mitgliedschaft/(einzelner) Geschäftsanteile"
    )
    KEY_COOP_SHARES_TRANSFER_EURO = "Übertragung Genossenschaftsanteile"
    KEY_COOP_SHARES_TRANSFER_FROM_TO = "Übertragung an/von"
    KEY_COOP_SHARES_TRANSFER_DATE = "Datum der Übertragung"
    KEY_COOP_SHARES_PAYBACK_EURO = "Ausgezahltes Geschäftsguthaben"
    KEY_COMMENT = "Kommentar"

    # Determine maximum number of shares a member has
    max_shares = Member.objects.annotate(
        purchase_transactions_count=Count(
            "coopsharetransaction",
            filter=models.Q(
                coopsharetransaction__transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE
            ),
        )
    ).aggregate(max_purchase_transactions=Max("purchase_transactions_count"))[
        "max_purchase_transactions"
    ]

    # Generate column headers for each share ownership entry
    share_cols = {}
    for i in range(1, max_shares + 1):
        share_cols[f"KEY_COOP_SHARES_{i}_EURO"] = f"GAnteile in € {i}. Zeichnung"
        share_cols[f"KEY_COOP_SHARES_{i}_ENTRY_DATE"] = f"Eintrittsdatum {i}. Zeichnung"

    output, writer = begin_csv_string(
        [
            KEY_MEMBER_NO,
            KEY_FIRST_NAME,
            KEY_LAST_NAME,
            KEY_ADDRESS,
            KEY_ADDRESS2,
            KEY_POSTCODE,
            KEY_CITY,
            KEY_BIRTHDATE,
            KEY_TELEPHONE,
            KEY_EMAIL,
            KEY_COOP_SHARES_TOTAL,
            KEY_COOP_SHARES_TOTAL_EURO,
            *share_cols.values(),
            KEY_COOP_SHARES_CANCELLATION_DATE,
            KEY_COOP_SHARES_CANCELLATION_AMOUNT,
            KEY_COOP_SHARES_CANCELLATION_CONTRACT_END_DATE,
            KEY_COOP_SHARES_TRANSFER_EURO,
            KEY_COOP_SHARES_TRANSFER_FROM_TO,
            KEY_COOP_SHARES_TRANSFER_DATE,
            KEY_COOP_SHARES_PAYBACK_EURO,
            KEY_COMMENT,
        ]
    )
    for entry in Member.objects.order_by("member_no"):
        coop_shares = entry.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE
        ).order_by("timestamp")
        last_cancelled_coop_shares = entry.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION
        ).order_by("-timestamp")
        if len(last_cancelled_coop_shares) > 0:
            last_cancelled_coop_shares = last_cancelled_coop_shares[0]
        else:
            last_cancelled_coop_shares = None

        today = date.today()
        # skip future members. TODO: check cancellation, when must old members be removed from the list?
        if entry.coop_entry_date is None or entry.coop_entry_date > today:
            continue

        transfered_to = entry.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.TRANSFER_OUT
        )
        transfered_from = entry.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN
        )

        data = {
            KEY_MEMBER_NO: entry.member_no,
            KEY_FIRST_NAME: entry.first_name,
            KEY_LAST_NAME: entry.last_name,
            KEY_ADDRESS: entry.street,
            KEY_ADDRESS2: entry.street_2,
            KEY_POSTCODE: entry.postcode,
            KEY_CITY: entry.city,
            KEY_BIRTHDATE: format_date(entry.birthdate),
            KEY_TELEPHONE: entry.phone_number,
            KEY_EMAIL: entry.email,
            KEY_COOP_SHARES_TOTAL: entry.coop_shares_quantity,
            KEY_COOP_SHARES_TOTAL_EURO: format_currency(
                entry.coop_shares_total_value()
            ),
            KEY_COOP_SHARES_CANCELLATION_DATE: format_date(
                last_cancelled_coop_shares.timestamp
            )
            if last_cancelled_coop_shares and last_cancelled_coop_shares.valid_at
            else "",
            KEY_COOP_SHARES_CANCELLATION_AMOUNT: format_currency(
                last_cancelled_coop_shares.total_price
            )
            if last_cancelled_coop_shares and last_cancelled_coop_shares.valid_at
            else "",
            KEY_COOP_SHARES_CANCELLATION_CONTRACT_END_DATE: format_date(
                last_cancelled_coop_shares.valid_at
            )
            if last_cancelled_coop_shares and last_cancelled_coop_shares.valid_at
            else "",
            KEY_COOP_SHARES_PAYBACK_EURO: "",  # TODO: how??? Cancelled coop shares?
            KEY_COMMENT: "",  # TODO: join comment log entries?
        }

        for i, share in enumerate(coop_shares, start=1):
            data[share_cols[f"KEY_COOP_SHARES_{i}_EURO"]] = format_currency(
                share.total_price
            )
            data[share_cols[f"KEY_COOP_SHARES_{i}_ENTRY_DATE"]] = format_date(
                share.valid_at
            )

        transfer_euro_amount = (
            sum(map(lambda x: x.quantity, transfered_to))
            + sum(map(lambda x: x.quantity, transfered_from))
        ) * settings.COOP_SHARE_PRICE
        transfer_euro_string = (
            "" if transfer_euro_amount == 0 else format_currency(transfer_euro_amount)
        )

        transfer_to_string = ", ".join(
            map(
                lambda x: f"an {x.transfer_member.first_name} {x.transfer_member.last_name}: {format_currency(abs(x.quantity) * settings.COOP_SHARE_PRICE)}  €",
                transfered_to,
            )
        )
        transfer_from_string = ", ".join(
            map(
                lambda x: f"von {x.transfer_member.first_name} {x.transfer_member.last_name}: {format_currency(x.quantity * settings.COOP_SHARE_PRICE)} €",
                transfered_from,
            )
        )
        transfer_to_date = ", ".join(
            map(
                lambda x: f"an {x.transfer_member.first_name} {x.transfer_member.last_name}: {format_date(x.valid_at)}",
                transfered_to,
            )
        )
        transfer_from_date = ", ".join(
            map(
                lambda x: f"von {x.transfer_member.first_name} {x.transfer_member.last_name}: {format_date(x.valid_at)}",
                transfered_from,
            )
        )
        data[KEY_COOP_SHARES_TRANSFER_EURO] = transfer_euro_string
        if not transfer_to_string or not transfer_from_string:
            data[KEY_COOP_SHARES_TRANSFER_FROM_TO] = (
                transfer_to_string or transfer_from_string
            )
            data[KEY_COOP_SHARES_TRANSFER_DATE] = transfer_to_date or transfer_from_date
        else:
            data[KEY_COOP_SHARES_TRANSFER_FROM_TO] = (
                transfer_to_string + " | " + transfer_from_string
            )
            data[KEY_COOP_SHARES_TRANSFER_DATE] = (
                transfer_to_date + " | " + transfer_from_date
            )

        writer.writerow(data)

    filename = f"Mitgliederliste_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    mime_type, _ = mimetypes.guess_type(filename)
    response = HttpResponse("".join(output.csv_string), content_type=mime_type)
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response
