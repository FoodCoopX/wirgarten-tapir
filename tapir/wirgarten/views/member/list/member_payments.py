from collections import defaultdict
from copy import copy
from datetime import datetime
from typing import Dict
from urllib.parse import unquote

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.member import PaymentAmountEditForm
from tapir.wirgarten.models import (
    CoopShareTransaction,
    EditFuturePaymentLogEntry,
    Member,
    Payment,
    Subscription,
)
from tapir.wirgarten.service.payment import get_next_payment_date
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
    get_product_price,
)
from tapir.wirgarten.utils import get_today
from tapir.wirgarten.views.mixin import PermissionOrSelfRequiredMixin


class MemberPaymentsView(
    PermissionOrSelfRequiredMixin, generic.TemplateView, generic.base.ContextMixin
):
    template_name = "wirgarten/member/member_payments.html"
    permission_required = Permission.Payments.VIEW

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_id = kwargs["pk"]

        cache = {}
        context["payments"] = self.get_payments_row(member_id, cache=cache)
        context["member"] = Member.objects.get(pk=member_id)

        return context

    def get_payments_row(self, member_id, cache: Dict):
        prev_payments = get_previous_payments(member_id, cache=cache)
        future_payments = generate_future_payments(member_id, cache=cache)

        for due_date, payments in future_payments.items():
            if due_date in prev_payments:
                prev_payments[due_date].extend(
                    [
                        p
                        for p in payments
                        if p.get("type", None)
                        not in set(
                            map(lambda x: x.get("type", None), prev_payments[due_date])
                        )
                    ]
                )
            else:
                prev_payments[due_date] = payments

        return sorted(
            [v for sublist in prev_payments.values() for v in sublist],
            key=lambda x: x["due_date"].isoformat() + x.get("type", ""),
        )


def sub_to_dict(sub, cache: Dict):
    if type(sub) is dict:
        return sub

    price = get_product_price(sub.product, sub.start_date, cache=cache).price
    return {
        "quantity": sub.quantity,
        "product": {
            "name": sub.product.name,
            "type": {"name": sub.product.type.name},
            "price": price,
        },
        "solidarity_price_percentage": sub.solidarity_price_percentage,
        "solidarity_price_absolute": sub.solidarity_price_absolute,
        "total_price": sub.total_price(),
        "price_override": sub.price_override,
    }


def payment_to_dict(payment: Payment, cache: Dict) -> dict:
    subs = (
        [
            {
                "quantity": tx.quantity,
                "product": {
                    "name": _("Genossenschaftsanteile"),
                    "price": tx.share_price,
                },
                "total_price": int(tx.quantity * tx.share_price),
            }
            for tx in CoopShareTransaction.objects.filter(payment=payment)
        ]
        if payment.type == "Genossenschaftsanteile"
        else list(
            map(
                lambda x: sub_to_dict(x, cache=cache),
                Subscription.objects.filter(
                    mandate_ref=payment.mandate_ref,
                    start_date__lte=payment.due_date,
                    end_date__gt=payment.due_date,
                    product__type__name=payment.type,
                ),
            )
        )
    )

    return {
        "id": payment.id,
        "type": payment.type,
        "due_date": payment.due_date,
        "mandate_ref": payment.mandate_ref,
        "amount": float(round(payment.amount, 2)),
        "calculated_amount": round(
            sum(map(lambda x: float(x["total_price"]), subs)), 2
        ),
        "subs": [sub_to_dict(sub, cache=cache) for sub in subs],
        "status": payment.status,
        "edited": payment.edited,
        "upcoming": (get_today() - payment.due_date).days < 0
        and not payment.transaction,
    }


def get_previous_payments(member_id, cache: Dict) -> dict:
    payments_dict = defaultdict(list)
    payments = Payment.objects.filter(mandate_ref__member_id=member_id).order_by(
        "-due_date"
    )

    for payment in payments:
        payment_dict = payment_to_dict(payment, cache=cache)
        payments_dict[payment_dict["due_date"]].append(payment_dict)

    return dict(payments_dict)


def generate_future_payments(member_id, limit: int = None, cache: Dict = None):
    subs = get_active_and_future_subscriptions(cache=cache).filter(member_id=member_id)
    max_end_date = subs.aggregate(Max("end_date"))["end_date__max"]

    payments_per_due_date = {}
    if not max_end_date:
        return payments_per_due_date

    next_payment_date = get_next_payment_date(cache=cache)
    while next_payment_date <= max_end_date and (
        limit is None or len(payments_per_due_date) < limit
    ):
        payments_per_due_date[next_payment_date] = []
        active_subs = subs.filter(
            start_date__lte=next_payment_date, end_date__gte=next_payment_date
        )
        for sub in active_subs:
            due_date = next_payment_date
            amount = sub.total_price()
            payments_per_due_date[next_payment_date].append(
                {
                    "type": sub.product.type.name,
                    "due_date": due_date,
                    "mandate_ref": sub.mandate_ref,
                    "amount": amount,
                    "calculated_amount": amount,
                    "subs": [sub_to_dict(sub, cache=cache)],
                    "status": Payment.PaymentStatus.DUE,
                    "edited": False,
                    "upcoming": True,
                }
            )
        if len(payments_per_due_date[next_payment_date]) == 0:
            del payments_per_due_date[next_payment_date]

        next_payment_date += relativedelta(months=1)

    return payments_per_due_date


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Payments.MANAGE)
@csrf_protect
def get_payment_amount_edit_form(request, **kwargs):
    query_params = {
        k: v
        for k, v in map(
            lambda kv: kv.split("="), request.environ["QUERY_STRING"].split("&")
        )
    }
    kwargs["initial_amount"] = float(query_params["amount"].replace(",", "."))
    kwargs["payment_type"] = unquote(query_params["type"])

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
                type=kwargs["payment_type"],
                due_date=datetime.strptime(form.payment_due_date, "%d.%m.%Y"),
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
