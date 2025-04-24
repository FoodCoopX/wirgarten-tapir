from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.configuration.parameter import get_parameter_value
from tapir.log.models import TextLogEntry
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.member import (
    CancellationReasonForm,
    PersonalDataForm,
    SubscriptionRenewalForm,
    TrialCancellationForm,
    WaitingListForm,
)
from tapir.wirgarten.forms.pickup_location import PickupLocationChoiceForm
from tapir.wirgarten.forms.registration.coop_shares import CooperativeShareForm
from tapir.wirgarten.forms.registration.payment_data import PaymentDataForm
from tapir.wirgarten.forms.subscription import AdditionalProductForm, BaseProductForm
from tapir.wirgarten.models import (
    Member,
    MemberPickupLocation,
    PickupLocation,
    ProductType,
    QuestionaireCancellationReasonResponse,
    SubscriptionChangeLogEntry,
    WaitingListEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import calculate_pickup_location_change_date
from tapir.wirgarten.service.member import (
    buy_cooperative_shares,
    create_wait_list_entry,
    get_next_contract_start_date,
    send_contract_change_confirmation,
    send_order_confirmation,
)
from tapir.wirgarten.service.payment import (
    get_active_subscriptions_grouped_by_product_type,
)
from tapir.wirgarten.service.products import (
    get_next_growing_period,
    is_product_type_available,
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.tapirmail import Events
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

        TransactionalTrigger.fire_action(Events.MEMBERAREA_CHANGE_DATA, member.email)

        member.save()

    return get_form_modal(
        request=request,
        form_class=PersonalDataForm,
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
    cache = {}
    kwargs["cache"] = cache
    check_permission_or_self(member_id, request)

    member = Member.objects.get(pk=member_id)
    next_month = get_today(cache=cache) + relativedelta(months=1, day=1)
    kwargs["initial"] = {
        "subs": get_active_subscriptions_grouped_by_product_type(
            member, reference_date=next_month, cache=cache
        ),
    }

    if member.pickup_location:
        kwargs["initial"]["initial"] = member.pickup_location.id

    kwargs["member"] = member

    @transaction.atomic
    def update_pickup_location(form):
        pickup_location_id = form.cleaned_data["pickup_location"].id
        change_date = (
            calculate_pickup_location_change_date(cache=cache)
            if member.pickup_location is not None
            else get_today(cache=cache)
        )
        old_pickup_location = member.pickup_location

        member_pickup_locations = MemberPickupLocation.objects.filter(member=member)
        member_pickup_location_valid_from_same_date = member_pickup_locations.filter(
            valid_from=change_date
        )
        if member_pickup_location_valid_from_same_date.exists():
            found = member_pickup_location_valid_from_same_date.first()
            found.pickup_location_id = pickup_location_id
            found.save()
        else:
            MemberPickupLocation.objects.create(
                member=member,
                pickup_location_id=pickup_location_id,
                valid_from=change_date,
            )

        MemberPickupLocation.objects.filter(
            member=member, valid_from__gt=change_date
        ).delete()

        new_pickup_location = PickupLocation.objects.get(id=pickup_location_id)
        change_date_str = format_date(change_date)
        TextLogEntry().populate(
            actor=request.user,
            user=member,
            text=f"Abholort geändert zum {change_date_str}: {old_pickup_location} -> {new_pickup_location}",
        ).save()

        TransactionalTrigger.fire_action(
            Events.MEMBERAREA_CHANGE_PICKUP_LOCATION,
            member.email,
            {
                "pickup_location": new_pickup_location.name,
                "pickup_location_start_date": change_date_str,
            },
        )

    return get_form_modal(
        request=request,
        form_class=PickupLocationChoiceForm,
        handler=update_pickup_location,
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
        form_class=WaitingListForm,
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
        form_class=WaitingListForm,
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
    kwargs["member_id"] = member_id
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
        form_class=SubscriptionRenewalForm,
        handler=lambda x: save(x),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_add_subscription_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    cache = {}
    kwargs["cache"] = cache

    check_permission_or_self(member_id, request)

    product_type_name = request.GET.get("productType")
    if product_type_name is None:
        raise Exception("productType not specified")

    product_type = get_object_or_404(ProductType, name=product_type_name)

    is_base_product_type = (
        BaseProductTypeService.get_base_product_type(cache=cache) == product_type
    )

    if is_base_product_type:
        form_type = BaseProductForm
        next_start_date = get_next_contract_start_date(cache=cache)
        next_period = get_next_growing_period(cache=cache)
        if not is_product_type_available(
            product_type.id,
            next_start_date,
            cache=cache,
        ) and (
            next_period
            and not is_product_type_available(
                product_type.id,
                next_period.start_date,
                cache=cache,
            )
        ):
            member = Member.objects.get(id=member_id)
            # FIXME: better don't even show the form to a member, just one button to be added to the waitlist
            wl_kwargs = kwargs.copy()
            wl_kwargs["initial"] = {
                "first_name": member.first_name,
                "last_name": member.last_name,
                "email": member.email,
                "privacy_consent": (member.privacy_consent is not None),
            }
            return get_harvest_shares_waiting_list_form(request, **wl_kwargs)

    else:
        kwargs["product_type_id"] = product_type.id
        form_type = AdditionalProductForm

    kwargs["is_admin"] = request.user.has_perm(Permission.Accounts.MANAGE)
    kwargs["member_id"] = member_id
    kwargs["choose_growing_period"] = True

    @transaction.atomic
    def save(form):
        member = Member.objects.get(id=member_id)

        if is_base_product_type:
            date_filter = next_start_date
            if next_period:
                date_filter = max(next_start_date, next_period.start_date)

            if (
                get_active_and_future_subscriptions()
                .filter(
                    cancellation_ts__isnull=True,
                    member_id=member_id,
                    end_date__gt=date_filter,
                )
                .exists()
            ):
                form.save(member_id=member_id)
                send_contract_change_confirmation(
                    member, form.subscriptions, cache=cache
                )
            else:
                form.save(member_id=member_id)
                send_order_confirmation(
                    member,
                    get_active_and_future_subscriptions(cache=cache).filter(
                        member=member
                    ),
                    cache=cache,
                )
        else:
            form.save(member_id=member_id)

        SubscriptionChangeLogEntry().populate(
            actor=request.user,
            user=member,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.ADDED,
            subscriptions=form.subscriptions,
        ).save()

    return get_form_modal(
        request=request,
        form_class=form_type,
        handler=save,
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_add_coop_shares_form(request, **kwargs):
    member_id = kwargs.pop("pk")

    check_permission_or_self(member_id, request)
    member = Member.objects.get(pk=member_id)
    cache = {}
    if not get_parameter_value(
        ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES, cache=cache
    ):
        # FIXME: better don't even show the form to a member, just one button to be added to the waitlist

        wl_kwargs = kwargs.copy()
        wl_kwargs["initial"] = {
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "privacy_consent": (member.privacy_consent is not None),
        }
        return get_coop_shares_waiting_list_form(request, **wl_kwargs)

    if member.is_in_coop_trial():
        raise PermissionDenied(
            "Mitglieder die im Probezeit sind dürfen keine weitere Anteile zeichnen"
        )

    today = get_today(cache=cache)
    kwargs["initial"] = {
        "outro_template": "wirgarten/registration/steps/coop_shares.validation.html"
    }
    kwargs["cache"] = cache
    return get_form_modal(
        request=request,
        form_class=CooperativeShareForm,
        handler=lambda x: buy_cooperative_shares(
            x.cleaned_data["cooperative_shares"] / settings.COOP_SHARE_PRICE,
            member_id,
            start_date=today,
        ),
        redirect_url_resolver=lambda _: member_detail_url(member_id),
        show_student_checkbox=False,
        member_is_student=member.is_student,
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
        form_class=TrialCancellationForm,
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
        form_class=PaymentDataForm,
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
        form_class=CancellationReasonForm,
        handler=save,
        redirect_url_resolver=lambda x: member_detail_url(member_id),
    )
