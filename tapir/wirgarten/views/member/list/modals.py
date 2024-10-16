from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.member import (
    CoopShareCancelForm,
    CoopShareTransferForm,
    NonTrialCancellationForm,
    PersonalDataForm,
)
from tapir.wirgarten.forms.subscription import (
    EditSubscriptionPriceForm,
    EditSubscriptionDatesForm,
)
from tapir.wirgarten.models import SubscriptionChangeLogEntry
from tapir.wirgarten.service.member import cancel_coop_shares, transfer_coop_shares
from tapir.wirgarten.utils import (
    check_permission_or_self,
    format_date,
    member_detail_url,
)
from tapir.wirgarten.views.modal import get_form_modal


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def get_coop_share_transfer_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form_class=CoopShareTransferForm,
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
        form_class=CoopShareCancelForm,
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
@permission_required(Permission.Accounts.MANAGE)
@csrf_protect
def get_member_personal_data_create_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form_class=PersonalDataForm,
        handler=lambda x: x.instance.save(),
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:member_list"),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def get_cancel_non_trial_form(request, **kwargs):
    member_id = kwargs["pk"]
    check_permission_or_self(member_id, request)

    @transaction.atomic
    def save(form: NonTrialCancellationForm):
        subs_to_cancel = form.get_subs_to_cancel()
        if len(subs_to_cancel) > 0:
            SubscriptionChangeLogEntry().populate(
                actor=request.user,
                user=form.member,
                change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
                subscriptions=subs_to_cancel,
            ).save()

        form.save()

    return get_form_modal(
        request=request,
        form_class=NonTrialCancellationForm,
        handler=save,
        redirect_url_resolver=lambda x: member_detail_url(member_id)
        + "?cancelled="
        + format_date(x),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
@permission_required(Permission.Accounts.MANAGE)
def get_edit_price_form(request, **kwargs):
    contract_id = kwargs["pk"]

    return get_form_modal(
        request=request,
        form_class=EditSubscriptionPriceForm,
        handler=lambda x: x.save(),
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:subscription_list")
        + "?contract="
        + str(contract_id),
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
@permission_required(Permission.Accounts.MANAGE)
def get_edit_dates_form(request, **kwargs):
    contract_id = kwargs["pk"]

    return get_form_modal(
        request=request,
        form_class=EditSubscriptionDatesForm,
        handler=lambda x: x.save(),
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:subscription_list")
        + "?contract="
        + str(contract_id),
        **kwargs,
    )
