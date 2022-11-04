import itertools
from copy import copy
from datetime import date
from importlib.resources import _

from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic
from django_filters import FilterSet, CharFilter
from django_filters.views import FilterView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.forms.member.forms import PaymentAmountEditForm
from tapir.wirgarten.models import (
    Member,
    Subscription,
    ShareOwnership,
    Payment,
    Deliveries,
    GrowingPeriod,
    MandateReference,
    EditFuturePaymentLogEntry,
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
    template_name = "wirgarten/member/member_filter.html"


class MemberDetailView(generic.DetailView):
    model = Member
    template_name = "wirgarten/member/member_detail.html"

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


def generate_future_payments(subs: list, prev_payments: list):
    prev_payments = set(map(lambda p: (p["mandate_ref"], p["due_date"]), prev_payments))

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
                due_date = next_payment_date.isoformat()

                if (mandate_ref, due_date) not in prev_payments:
                    amount = get_payment_amount_for_subs(values)

                    payments.append(
                        {
                            "due_date": due_date,
                            "mandate_ref": mandate_ref,
                            "amount": amount,
                            "calculated_amount": amount,
                            "subs": active_subs,
                            "status": Payment.PaymentStatus.DUE,
                            "edited": False,
                            "upcoming": True,
                        }
                    )

        next_payment_date += relativedelta(months=1)

    return payments


def get_payment_amount_for_subs(subs: [Subscription]) -> float:
    return round(
        sum(
            map(
                lambda x: get_sub_total(x),
                subs,
            )
        ),
        2,
    )


def get_sub_total(position):
    if type(position) == Subscription:
        position = {
            "quantity": position.quantity,
            "product": {
                "price": position.product.price,
            },
            "solidarity_price": position.solidarity_price,
        }
    return (
        position["quantity"]
        * float(position["product"]["price"])
        * (1 + position.get("solidarity_price", 0.0))
    )


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


def payment_to_dict(payment: Payment) -> dict:
    subs = get_subs_or_shares(payment.mandate_ref, payment.due_date)
    return {
        "due_date": payment.due_date.isoformat(),
        "mandate_ref": payment.mandate_ref,
        "amount": float(round(payment.amount, 2)),
        "calculated_amount": get_payment_amount_for_subs(subs),
        "subs": subs,
        "status": payment.status,
        "edited": payment.edited,
        "upcoming": (date.today() - payment.due_date).days < 0,
    }


def get_previous_payments(member_id) -> [dict]:
    return list(
        map(
            lambda x: payment_to_dict(x),
            Payment.objects.filter(mandate_ref__member_id=member_id),
        )
    )


class MemberPaymentsView(generic.TemplateView, generic.base.ContextMixin):
    template_name = "wirgarten/member/member_payments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_id = kwargs["pk"]

        subs = Subscription.objects.filter(member=member_id)

        context["payments"] = self.get_payments_row(member_id, subs)
        context["member"] = Member.objects.get(pk=member_id)

        return context

    def get_payments_row(self, member_id, subs):
        prev_payments = get_previous_payments(member_id)
        future_payments = generate_future_payments(subs, prev_payments)

        return sorted(
            prev_payments + future_payments,
            key=lambda x: x["due_date"] + x["mandate_ref"].ref,
        )


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
    template_name = "wirgarten/member/member_deliveries.html"

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


@transaction.atomic
def get_payment_amount_edit_form(request, **kwargs):
    if request.method == "POST":
        form = PaymentAmountEditForm(request.POST, **kwargs)
        if form.is_valid():
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

            create_payment_edit_logentry(form, kwargs, new_payment, request)

            return HttpResponseRedirect(
                reverse_lazy(
                    "wirgarten:member_payments",
                    kwargs={"pk": kwargs["member_id"]},
                    current_app="wirgarten",
                )
            )

    else:
        form = PaymentAmountEditForm(None, **kwargs)
        return render(
            request, "wirgarten/member/member_payments_edit_form.html", {"form": form}
        )


def create_payment_edit_logentry(form, kwargs, new_payment, request):
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
