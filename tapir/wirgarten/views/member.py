import itertools
import mimetypes
from copy import copy
from datetime import date, datetime
from importlib.resources import _

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django_filters import (
    FilterSet,
    CharFilter,
    ChoiceFilter,
    OrderingFilter,
    ModelChoiceFilter,
)
from django_filters.views import FilterView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import (
    WEEKLY,
    EVEN_WEEKS,
    ODD_WEEKS,
    ProductTypes,
    Permission,
)
from tapir.wirgarten.forms.member.forms import (
    PaymentAmountEditForm,
    CoopShareTransferForm,
    PersonalDataForm,
    WaitingListForm,
    TrialCancellationForm,
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
    ShareOwnership,
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
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
    get_active_pickup_locations,
)
from tapir.wirgarten.service.file_export import begin_csv_string
from tapir.wirgarten.service.member import (
    transfer_coop_shares,
    create_member,
    create_wait_list_entry,
    buy_cooperative_shares,
    get_next_trial_end_date,
    get_subscriptions_in_trial_period,
    get_next_contract_start_date,
    send_cancellation_confirmation_email,
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
)
from tapir.wirgarten.utils import format_date
from tapir.wirgarten.views.mixin import PermissionOrSelfRequiredMixin
from tapir.wirgarten.views.modal import get_form_modal


# FIXME: this file needs some serious refactoring. Some of the functions should either be generalized service functions or private functions.


class MemberFilter(FilterSet):
    first_name = CharFilter(lookup_expr="icontains")
    last_name = CharFilter(lookup_expr="icontains")
    email = CharFilter(lookup_expr="icontains")
    o = OrderingFilter(
        label=_("Sortierung"),
        initial=0,
        choices=(
            ("-created_at", "⮟ Registriert am"),
            ("created_at", "⮝ Registriert am"),
        ),
        required=True,
        empty_label=None,
    )

    class Meta:
        model = Member
        fields = ["first_name", "last_name", "email"]

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


class MemberDetailView(PermissionOrSelfRequiredMixin, generic.DetailView):
    model = Member
    template_name = "wirgarten/member/member_detail.html"
    permission_required = Permission.Accounts.VIEW

    def get_user_pk(self):
        return self.kwargs["pk"]

    def get_context_data(self, **kwargs):
        context = super(MemberDetailView, self).get_context_data()

        today = date.today()
        next_month = today + relativedelta(months=1)

        context["object"] = self.object
        context["subscriptions"] = get_active_subscriptions_grouped_by_product_type(
            self.object, next_month
        )

        context["sub_quantities"] = {
            k: sum(map(lambda x: x.quantity, v))
            for k, v in context["subscriptions"].items()
        }
        context["sub_totals"] = {
            k: sum(map(lambda x: x.get_total_price(), v))
            for k, v in context["subscriptions"].items()
        }

        product_types = get_active_product_types()
        for pt in product_types:
            if pt.name not in context["subscriptions"]:
                context["subscriptions"][pt.name] = []
                context["sub_quantities"][pt.name] = 0

        share_ownerships = list(ShareOwnership.objects.filter(member=self.object))
        context["coop_shares"] = list(
            map(
                lambda s: {
                    "quantity": s.quantity,
                    "share_price": s.share_price,
                    "timestamp": s.created_at.strftime("%d.%m.%Y"),
                },
                share_ownerships,
            )
        )

        context["coop_shares_total"] = sum(map(lambda x: x.quantity, share_ownerships))

        over_next_contract_start_date = get_next_contract_start_date() + relativedelta(
            months=1
        )
        additional_products_available = any(
            sub.end_date > over_next_contract_start_date
            for sub in context["subscriptions"][ProductTypes.HARVEST_SHARES]
        )

        context["available_product_types"] = {
            ProductTypes.HARVEST_SHARES: is_harvest_shares_available(),
            ProductTypes.CHICKEN_SHARES: additional_products_available
            and is_chicken_shares_available(),
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
            and is_bestellcoop_available(),
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

        next_payments = generate_future_payments(self.object.pk, prev_payments, 1)

        if len(next_payments) > 0:
            if "next_payment" not in context or (
                next_payments[0]["due_date"] < context["next_payment"]["due_date"]
            ):
                context["next_payment"] = next_payments[0]

        self.add_renewal_notice_context(context, next_month, today)

        context["next_trial_end_date"] = get_next_trial_end_date()
        if get_subscriptions_in_trial_period(self.object.pk).exists():
            context["show_trial_period_notice"] = True

        return context

    def add_renewal_notice_context(self, context, next_month, today):
        """
        Renewal notice:
         - show_renewal_warning = less than 3 months before next period starts
         - add_shares_disallowed = less than 1 month
         - renewal_status = "unknown", "renewed", "cancelled"
        """

        next_growing_period = get_next_growing_period(today)
        if (
            next_growing_period
            and (today + relativedelta(months=3)) > next_growing_period.start_date
        ):
            context["next_period"] = next_growing_period
            context["add_shares_disallowed"] = (
                next_month > next_growing_period.start_date
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
            if cancelled:
                context["renewal_status"] = "cancelled"
            elif (
                get_future_subscriptions(next_growing_period.start_date)
                .filter(member_id=self.object.pk)
                .exists()
            ):
                context["renewal_status"] = "renewed"
            else:
                context["renewal_status"] = "unknown"

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
                    ),
                },
            }

    def format_param(
        self, key: str, contract_end_date: str, next_growing_period: GrowingPeriod
    ):
        return get_parameter_value(key).format(
            member=self.object,
            contract_end_date=contract_end_date,
            next_period_start_date=format_date(next_growing_period.start_date),
            next_period_end_date=format_date(next_growing_period.end_date),
        )


@require_http_methods(["GET"])
@csrf_protect
@login_required
@transaction.atomic
def renew_contract_same_conditions(request, **kwargs):
    member_id = kwargs["pk"]
    new_subs = []
    next_period = get_next_growing_period()
    for sub in get_future_subscriptions().filter(member_id=member_id):
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
    Subscription.objects.bulk_create(new_subs)

    return HttpResponseRedirect(member_detail_url(member_id))


@require_http_methods(["GET"])
@csrf_protect
@login_required
@transaction.atomic
def cancel_contract_at_period_end(request, **kwargs):
    member_id = kwargs["pk"]
    # if not member_id == request.user.pk:
    #    raise PermissionDenied("A member can only cancel a contract themself.")

    now = datetime.now()
    subs = list(get_future_subscriptions().filter(member_id=member_id))
    for sub in subs:
        sub.cancellation_ts = now
        sub.save()

    send_cancellation_confirmation_email(member_id, subs[0].end_date, subs)

    return HttpResponseRedirect(member_detail_url(member_id) + "?cancelled=true")


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
                    "total_price": x.get_total_price(),
                },
                ShareOwnership.objects.filter(mandate_ref=mandate_ref),
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
        "total_price": float(price) * sub.solidarity_price * sub.quantity,
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


def get_next_delivery_date():
    now = date.today()
    delivery_day = get_parameter_value(Parameter.DELIVERY_DAY)
    if now.weekday() > delivery_day:
        next_delivery = now + relativedelta(days=(7 - now.weekday() % 7) + delivery_day)
    else:
        next_delivery = now + relativedelta(days=delivery_day - now.weekday())
    return next_delivery


def generate_future_deliveries(member: Member):
    deliveries = []
    next_delivery_date = get_next_delivery_date()
    last_growing_period = GrowingPeriod.objects.order_by("-end_date")[:1][0]
    subs = get_future_subscriptions().filter(member=member)
    while next_delivery_date <= last_growing_period.end_date:
        _, week_num, _ = next_delivery_date.isocalendar()
        even_week = week_num % 2 == 0

        active_subs = subs.filter(
            start_date__lte=next_delivery_date,
            end_date__gte=next_delivery_date,
            product__type__delivery_cycle__in=[
                WEEKLY[0],
                EVEN_WEEKS[0] if even_week else ODD_WEEKS[0],
            ],
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
@csrf_protect
@login_required
def get_member_personal_data_edit_form(request, **kwargs):
    pk = kwargs.pop("pk")

    check_permission_or_self(pk, request)

    def update_member(
        member_id,
        first_name,
        last_name,
        email,
        phone_number,
        street,
        street_2,
        postcode,
        city,
        birthdate,
    ):
        instance = Member.objects.get(pk=member_id)
        instance.first_name = first_name
        instance.last_name = last_name
        instance.email = email
        instance.phone_number = phone_number
        instance.street = street
        instance.street_2 = street_2
        instance.postcode = postcode
        instance.city = city
        instance.birthdate = birthdate
        instance.save()
        return instance

    return get_form_modal(
        request=request,
        form=PersonalDataForm,
        instance=Member.objects.get(pk=pk),
        handler=lambda x: update_member(
            member_id=pk,
            first_name=x.cleaned_data["first_name"],
            last_name=x.cleaned_data["last_name"],
            email=x.cleaned_data["email"],
            phone_number=x.cleaned_data["phone_number"],
            street=x.cleaned_data["street"],
            street_2=x.cleaned_data["street_2"],
            postcode=x.cleaned_data["postcode"],
            city=x.cleaned_data["city"],
            birthdate=x.cleaned_data["birthdate"],
        ),
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
        member.sepa_consent = datetime.now()
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
        handler=lambda x: create_member(x.instance),
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:member_list"),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_harvest_shares_waiting_list_form(request, **kwargs):
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
        handler=lambda x: x.save(
            member_id=member_id,
        ),
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

    return get_form_modal(
        request=request,
        form=CooperativeShareForm,
        handler=lambda x: buy_cooperative_shares(
            x.cleaned_data["cooperative_shares"], member_id
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
        redirect_url_resolver=lambda _: member_detail_url(member_id)
        + "?cancelled=true",
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

    filename = f"Warteliste-{waitlist_type_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    mime_type, _ = mimetypes.guess_type(filename)
    response = HttpResponse("".join(output.csv_string), content_type=mime_type)
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response


class SubscriptionListFilter(FilterSet):
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
    o = OrderingFilter(
        label=_("Sortierung"),
        initial=0,
        choices=(
            ("-created_at", "⮟ Abgeschlossen am"),
            ("created_at", "⮝ Abgeschlossen am"),
        ),
        required=True,
        empty_label=None,
    )

    class Meta:
        model = Subscription
        fields = []

    def __init__(self, data=None, *args, **kwargs):
        super(SubscriptionListFilter, self).__init__(data, *args, **kwargs)

        def get_default_period_filter_value():
            today = date.today()
            return (
                self.filters["period"]
                .queryset.filter(start_date__lte=today, end_date__gte=today)
                .first()
                .id
            )

        if data is None:
            data = {"o": "-created_at", "period": get_default_period_filter_value()}
        else:
            data = data.copy()

            if "o" not in data:
                data["o"] = "-created_at"

            if "period" not in data:
                data["period"] = get_default_period_filter_value()

        super(SubscriptionListFilter, self).__init__(data, *args, **kwargs)


class SubscriptionListView(PermissionRequiredMixin, FilterView):
    filterset_class = SubscriptionListFilter
    ordering = ["-created_at"]
    permission_required = Permission.Accounts.VIEW
    template_name = "wirgarten/subscription/subscription_filter.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next_trial_end_date"] = get_next_trial_end_date()
        context["latest_trial_start_date"] = context[
            "next_trial_end_date"
        ] + relativedelta(day=1)
        return context
