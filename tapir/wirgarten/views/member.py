import itertools
from datetime import date
from importlib.resources import _

from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import generic
from django_filters import FilterSet, CharFilter
from django_filters.views import FilterView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import (
    Member,
    Subscription,
    ShareOwnership,
    Payment,
    Deliveries,
    GrowingPeriod,
    MandateReference,
)
from tapir.wirgarten.parameters import Parameter


class MemberFilter(FilterSet):
    first_name = CharFilter(lookup_expr="icontains")
    last_name = CharFilter(lookup_expr="icontains")
    email = CharFilter(lookup_expr="icontains")

    class Meta:
        model = Member
        fields = ["first_name", "last_name", "email"]


class MemberListView(PermissionRequiredMixin, FilterView):
    filterset_class = MemberFilter
    ordering = ["date_joined"]
    permission_required = "coop.manage"


class MemberDetailView(generic.DetailView):
    model = Member

    def get_context_data(self, object):
        context = super(MemberDetailView, self).get_context_data()
        context["object"] = self.object
        context["subscriptions"] = get_grouped_subscribtions_for_member(self.object)

        shares = ShareOwnership.objects.filter(member=self.object)[0]
        context["coop_shares"] = f"""{shares.quantity} × {shares.share_price} €"""

        return context


def get_next_payment_date():
    now = date.today()
    due_day = get_due_day()

    if now.day < due_day:
        next_payment = now.replace(day=due_day)
    else:
        next_payment = now.replace(day=due_day) + relativedelta(months=1)
    return next_payment


def get_due_day():
    due_day = get_parameter_value(Parameter.PAYMENT_DUE_DAY)
    if due_day > 31:
        due_day = 31
    if due_day < 1:
        due_day = 1
    return due_day


def generate_future_payments(subs: list):
    payments = []
    next_payment_date = get_next_payment_date()
    last_growing_period = GrowingPeriod.objects.order_by("-end_date")[:1][0]
    while next_payment_date <= last_growing_period.end_date:
        active_subs = subs.filter(
            start_date__lte=next_payment_date, end_date__gte=next_payment_date
        )
        if active_subs.count() > 0:

            groups = itertools.groupby(active_subs, lambda v: v.mandate_ref)

            for mandate_ref, values in groups:
                values = list(values)

                payments.append(
                    {
                        "due_date": next_payment_date.isoformat(),
                        "mandate_ref": mandate_ref,
                        "amount": round(
                            sum(
                                map(
                                    lambda x: get_sub_total(x),
                                    values,
                                )
                            ),
                            2,
                        ),
                        "subs": active_subs,
                        "status": Payment.PaymentStatus.UPCOMING,
                    }
                )

        next_payment_date += relativedelta(months=1)

    return payments


def get_sub_total(sub):
    return sub.quantity * float(sub.product.price) * (1 + sub.solidarity_price)


def get_subs_or_shares(mandate_ref: MandateReference, date: date):
    subs = Subscription.objects.filter(
        mandate_ref=mandate_ref,
        start_date__lte=date,
        end_date__gt=date,
    )

    if subs.count() == 0:
        return list(
            map(
                lambda x: {
                    "amount": round(x.share_price, 2),
                    "quantity": x.quantity,
                    "product": {
                        "name": _("Genossenschaftsanteile"),
                        "price": x.share_price,
                    },
                },
                ShareOwnership.objects.filter(mandate_ref=mandate_ref),
            )
        )
    else:
        return subs


def get_previous_payments(member_id):
    return list(
        map(
            lambda x: {
                "due_date": x.due_date.isoformat(),
                "mandate_ref": x.mandate_ref,
                "amount": round(x.amount, 2),
                "subs": get_subs_or_shares(x.mandate_ref, x.due_date),
                "status": x.status,
            },
            Payment.objects.filter(mandate_ref__member_id=member_id),
        )
    )


class MemberPaymentsView(generic.TemplateView, generic.base.ContextMixin):
    template_name = "wirgarten/member_payments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_id = kwargs["pk"]

        subs = Subscription.objects.filter(member=member_id)

        context["payments"] = sorted(
            get_previous_payments(member_id) + generate_future_payments(subs),
            key=lambda x: x["due_date"],
        )
        context["member"] = Member.objects.get(pk=member_id)

        return context


def get_next_delivery_date():
    now = date.today()
    delivery_day = get_parameter_value(Parameter.DELIVERY_DAY)
    if now.weekday() > delivery_day:
        next_delivery = now + relativedelta(days=(7 - now.weekday() % 7) + delivery_day)
    else:
        next_delivery = now + relativedelta(days=delivery_day - now.weekday())
    return next_delivery


def generate_future_deliveries(subs, member: Member):
    deliveries = []
    next_delivery_date = get_next_delivery_date()
    last_growing_period = GrowingPeriod.objects.order_by("-end_date")[:1][0]
    while next_delivery_date <= last_growing_period.end_date:
        active_subs = subs.filter(
            start_date__lte=next_delivery_date, end_date__gte=next_delivery_date
        )
        if active_subs.count() > 0:
            deliveries.append(
                {
                    "delivery_date": next_delivery_date.isoformat(),
                    "pickup_location": member.pickup_location,
                    "subs": active_subs,
                }
            )

        next_delivery_date += relativedelta(days=7)

    return deliveries


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


class MemberDeliveriesView(generic.TemplateView, generic.base.ContextMixin):
    template_name = "wirgarten/member_deliveries.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_id = kwargs["pk"]

        subs = Subscription.objects.filter(member=member_id)

        member = Member.objects.get(pk=member_id)

        context["member"] = member
        context["deliveries"] = get_previous_deliveries(
            member
        ) + generate_future_deliveries(subs, member)

        return context


def get_grouped_subscribtions_for_member(member: Member):
    subscriptions = {}
    for sub in Subscription.objects.filter(member=member):
        product_type = sub.product.type.name
        if product_type not in subscriptions:
            subscriptions[product_type] = []

        subscriptions[product_type].append(sub)

    return subscriptions
