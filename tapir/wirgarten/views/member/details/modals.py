from datetime import timezone

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from tapir import settings
from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.configuration.parameter import get_parameter_value
from tapir.log.models import TextLogEntry
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.member.forms import (
    CancellationReasonForm,
    PersonalDataForm,
    SubscriptionRenewalForm,
    TrialCancellationForm,
    WaitingListForm,
)
from tapir.wirgarten.forms.pickup_location import PickupLocationChoiceForm
from tapir.wirgarten.forms.registration.bestellcoop import BestellCoopForm
from tapir.wirgarten.forms.registration.chicken_shares import ChickenShareForm
from tapir.wirgarten.forms.registration.coop_shares import CooperativeShareForm
from tapir.wirgarten.forms.registration.harvest_shares import HarvestShareForm
from tapir.wirgarten.forms.registration.payment_data import PaymentDataForm
from tapir.wirgarten.models import (
    Member,
    MemberPickupLocation,
    PickupLocation,
    QuestionaireCancellationReasonResponse,
    SubscriptionChangeLogEntry,
    WaitingListEntry,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import (
    calculate_pickup_location_change_date,
    get_next_delivery_date,
)
from tapir.wirgarten.service.member import (
    buy_cooperative_shares,
    create_wait_list_entry,
    send_order_confirmation,
)
from tapir.wirgarten.service.payment import (
    get_active_subscriptions_grouped_by_product_type,
)
from tapir.wirgarten.service.products import (
    get_future_subscriptions,
    get_next_growing_period,
    is_bestellcoop_available,
    is_harvest_shares_available,
)
from tapir.wirgarten.utils import (
    check_permission_or_self,
    format_date,
    get_now,
    get_today,
    member_detail_url,
)
from tapir.wirgarten.views.modal import get_form_modal


@require_http_methods(["GET", "POST"])
@csrf_protect
@login_required
def get_member_personal_data_edit_form(request, **kwargs):
    pk = kwargs.pop("pk")

    check_permission_or_self(pk, request)

    kwargs["can_edit_name_and_birthdate"] = request.user.has_perm(
        Permission.Accounts.MANAGE
    )

    @transaction.atomic
    def save(member: Member):
        orig = Member.objects.get(id=member.id)
        UpdateTapirUserLogEntry().populate(
            old_model=orig, new_model=member, user=member, actor=request.user
        ).save()

        member.save()

    return get_form_modal(
        request=request,
        form=PersonalDataForm,
        instance=Member.objects.get(pk=pk),
        handler=lambda x: save(x.instance),
        redirect_url_resolver=lambda _: member_detail_url(pk),
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
        "subs": get_active_subscriptions_grouped_by_product_type(member),
    }
    if member.pickup_location:
        kwargs["initial"]["initial"] = member.pickup_location.id

    @transaction.atomic
    def update_pickup_location(form):
        pickup_location_id = form.cleaned_data["pickup_location"].id

        change_date = (
            calculate_pickup_location_change_date()
            if member.pickup_location is not None
            else get_today()
        )

        qs = MemberPickupLocation.objects.filter(member=member)
        existing = qs.filter(valid_from=change_date)
        if existing.exists():
            found = existing.first()
            found.pickup_location_id = pickup_location_id
            found.save()
        else:
            MemberPickupLocation.objects.create(
                member=member,
                pickup_location_id=pickup_location_id,
                valid_from=change_date,
            )
        pl = PickupLocation.objects.get(id=pickup_location_id)
        TextLogEntry().populate(
            actor=request.user,
            user=member,
            text=f"Abholort geändert zum {format_date(change_date)}: {member.pickup_location} -> {pl}",
        ).save()

    return get_form_modal(
        request=request,
        form=PickupLocationChoiceForm,
        handler=lambda x: update_pickup_location(x),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
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

    @transaction.atomic
    def save(form: SubscriptionRenewalForm):
        member = Member.objects.get(id=member_id)

        form.save(
            member_id=member_id,
        )

        SubscriptionChangeLogEntry().populate(
            actor=request.user,
            user=member,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.RENEWED,
            subscriptions=form.subs,
        ).save()

    return get_form_modal(
        request=request,
        form=SubscriptionRenewalForm,
        handler=lambda x: save(x),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_add_harvest_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    check_permission_or_self(member_id, request)

    member = Member.objects.get(pk=member_id)
    next_period = get_next_growing_period()
    if not is_harvest_shares_available() and not is_harvest_shares_available(
        next_period.start_date
    ):
        # FIXME: better don't even show the form to a member, just one button to be added to the waitlist
        wl_kwargs = kwargs.copy()
        wl_kwargs["initial"] = {
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "privacy_consent": (member.privacy_consent is not None),
        }
        return get_harvest_shares_waiting_list_form(request, **wl_kwargs)

    @transaction.atomic
    def save(form: HarvestShareForm):
        if (
            get_future_subscriptions()
            .filter(
                cancellation_ts__isnull=True,
                member_id=member_id,
                end_date__gt=max(form.start_date, form.growing_period.start_date)
                if hasattr(form, "growing_period")
                else form.start_date,
            )
            .exists()
        ):
            form.save(send_email=True)
        else:
            form.save(send_email=False)
            send_order_confirmation(
                member, get_future_subscriptions().filter(member=member)
            )

        SubscriptionChangeLogEntry().populate(
            actor=request.user,
            user=member,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.ADDED,
            subscriptions=form.subs,
        ).save()

    kwargs["is_admin"] = request.user.has_perm(Permission.Accounts.MANAGE)
    kwargs["member_id"] = member_id
    kwargs["choose_growing_period"] = True
    return get_form_modal(
        request=request,
        form=HarvestShareForm,
        handler=lambda x: save(x),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_add_chicken_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    check_permission_or_self(member_id, request)
    kwargs["choose_growing_period"] = True
    kwargs["member_id"] = member_id

    @transaction.atomic
    def save(form: ChickenShareForm):
        form.save(member_id=member_id, send_mail=True)

        member = Member.objects.get(id=member_id)

        SubscriptionChangeLogEntry().populate(
            actor=request.user,
            user=member,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.ADDED,
            subscriptions=form.subs,
        ).save()

    return get_form_modal(
        request=request,
        form=ChickenShareForm,
        handler=lambda x: save(x),
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

    @transaction.atomic
    def save(form: BestellCoopForm):
        form.save(member_id=member_id)

        member = Member.objects.get(id=member_id)

        SubscriptionChangeLogEntry().populate(
            actor=request.user,
            user=member,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.ADDED,
            subscriptions=[form.sub],
        ).save()

    return get_form_modal(
        request=request,
        form=BestellCoopForm,
        handler=lambda x: save(x),
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

    today = get_today()
    return get_form_modal(
        request=request,
        form=CooperativeShareForm,
        handler=lambda x: buy_cooperative_shares(
            x.cleaned_data["cooperative_shares"] / settings.COOP_SHARE_PRICE,
            member_id,
            start_date=today,
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

    @transaction.atomic
    def save(form: TrialCancellationForm):
        subs_to_cancel = form.get_subs_to_cancel()
        cancel_coop = form.is_cancel_coop_selected()
        if cancel_coop:
            TextLogEntry().populate(
                text="Beitrittserklärung zur Genossenschaft zurückgezogen",
                user=form.member,
                actor=request.user,
            ).save()
        if len(subs_to_cancel) > 0:
            SubscriptionChangeLogEntry().populate(
                actor=request.user,
                user=form.member,
                change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
                subscriptions=subs_to_cancel,
            ).save()

        return form.save(skip_emails=member_id != request.user.id)

    return get_form_modal(
        request=request,
        form=TrialCancellationForm,
        handler=save,
        redirect_url_resolver=lambda x: member_detail_url(member_id)
        + "?cancelled="
        + format_date(x),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@csrf_protect
@login_required
def get_member_payment_data_edit_form(request, **kwargs):
    member_id = kwargs.pop("pk")
    check_permission_or_self(member_id, request)

    instance = Member.objects.get(pk=member_id)

    def update_payment_data(member: Member, account_owner: str, iban: str):
        member.account_owner = account_owner
        member.iban = iban
        member.sepa_consent = get_now()

        orig = Member.objects.get(id=member.id)
        UpdateTapirUserLogEntry().populate(
            old_model=orig, new_model=member, user=member, actor=request.user
        ).save()

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
        ),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_cancellation_reason_form(request, **kwargs):
    member_id = kwargs["pk"]
    check_permission_or_self(member_id, request)

    @transaction.atomic
    def save(form: CancellationReasonForm):
        for reason in form.cleaned_data["reason"]:
            QuestionaireCancellationReasonResponse.objects.create(
                member_id=member_id, reason=reason, custom=False
            )
        if form.cleaned_data["custom_reason"]:
            QuestionaireCancellationReasonResponse.objects.create(
                member_id=member_id,
                reason=form.cleaned_data["custom_reason"],
                custom=True,
            )

    return get_form_modal(
        request=request,
        form=CancellationReasonForm,
        handler=save,
        redirect_url_resolver=lambda x: member_detail_url(member_id),
    )
