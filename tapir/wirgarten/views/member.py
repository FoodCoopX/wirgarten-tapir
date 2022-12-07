import itertools
import mimetypes
from copy import copy
from datetime import date, datetime
from importlib.resources import _

from dateutil import parser
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django_filters import FilterSet, CharFilter, ChoiceFilter
from django_filters.views import FilterView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, ODD_WEEKS, ProductTypes
from tapir.wirgarten.forms.member.forms import (
    PaymentAmountEditForm,
    CoopShareTransferForm,
    PersonalDataForm,
    WaitingListForm,
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
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.file_export import begin_csv_string
from tapir.wirgarten.service.member import (
    transfer_coop_shares,
    create_member,
    create_wait_list_entry,
    buy_cooperative_shares,
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
)
from tapir.wirgarten.views.exported_files import EXPORT_PERMISSION
from tapir.wirgarten.views.modal import get_form_modal


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
        context["subscriptions"] = get_active_subscriptions_grouped_by_product_type(
            self.object
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
                context["subscriptions"][pt.name] = [{"quantity": 0}]
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

        context["available_product_types"] = {
            ProductTypes.HARVEST_SHARES: is_harvest_shares_available(),
            ProductTypes.CHICKEN_SHARES: is_chicken_shares_available(),
            ProductTypes.BESTELLCOOP: is_bestellcoop_available(),
        }

        if self.object.pickup_location:
            context["pickup_location_map_data"] = get_pickup_locations_map_data(
                [self.object.pickup_location],
                PickupLocationCapability.objects.filter(
                    pickup_location=self.object.pickup_location
                ),
            )

        context["deliveries"] = generate_future_deliveries(self.object)

        # FIXME: it should be easier than this to get the next payments, refactor to service somehow
        prev_payments = get_previous_payments(self.object.pk)
        now = datetime.now()
        for payment in prev_payments:
            if parser.parse(payment["due_date"]) > now:
                context["next_payment"] = payment
            else:
                break

        next_payments = generate_future_payments(self.object.pk, prev_payments, 1)

        if len(next_payments) > 0:
            if "next_payment" not in context or (
                next_payments[0]["due_date"] < context["next_payment"]["due_date"]
            ):
                context["next_payment"] = next_payments[0]

        return context


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
                due_date = next_payment_date.isoformat()

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
        "due_date": payment.due_date.isoformat(),
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


class MemberPaymentsView(generic.TemplateView, generic.base.ContextMixin):
    template_name = "wirgarten/member/member_payments.html"

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


class MemberDeliveriesView(generic.TemplateView, generic.base.ContextMixin):
    template_name = "wirgarten/member/member_deliveries.html"

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
def get_member_personal_data_edit_form(request, **kwargs):
    pk = kwargs.pop("pk")

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
        redirect_url_resolver=lambda x: reverse_lazy(
            "wirgarten:member_detail", kwargs={"pk": x.id}
        ),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_member_payment_data_edit_form(request, **kwargs):
    instance = Member.objects.get(pk=kwargs.pop("pk"))

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
        redirect_url_resolver=lambda x: reverse_lazy(
            "wirgarten:member_detail", kwargs={"pk": x.id}
        ),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_pickup_location_choice_form(request, **kwargs):
    member = Member.objects.get(pk=kwargs.pop("pk"))
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
        redirect_url_resolver=lambda x: reverse_lazy(
            "wirgarten:member_detail", kwargs={"pk": member.id}
        ),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
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
def get_add_harvest_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

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
        redirect_url_resolver=lambda x: reverse_lazy(
            "wirgarten:member_detail", kwargs={"pk": member_id}
        ),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_add_chicken_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    if not is_chicken_shares_available():
        raise Exception("Keine Hühneranteile verfügbar")

    return get_form_modal(
        request=request,
        form=ChickenShareForm,
        handler=lambda x: x.save(
            member_id=member_id,
        ),
        redirect_url_resolver=lambda x: reverse_lazy(
            "wirgarten:member_detail", kwargs={"pk": member_id}
        ),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_add_bestellcoop_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    if not is_bestellcoop_available():
        raise Exception("BestellCoop nicht verfügbar")

    return get_form_modal(
        request=request,
        form=BestellCoopForm,
        handler=lambda x: x.save(
            member_id=member_id,
        ),
        redirect_url_resolver=lambda x: reverse_lazy(
            "wirgarten:member_detail", kwargs={"pk": member_id}
        ),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_add_coop_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

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
        redirect_url_resolver=lambda x: reverse_lazy(
            "wirgarten:member_detail", kwargs={"pk": member_id}
        ),
        **kwargs,
    )


class WaitingListFilter(PermissionRequiredMixin, FilterSet):
    permission_required = "coop.manage"

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
    permission_required = "coop.manage"
    template_name = "wirgarten/waitlist/waitlist_filter.html"


@require_GET
@csrf_protect
@permission_required(EXPORT_PERMISSION)
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
