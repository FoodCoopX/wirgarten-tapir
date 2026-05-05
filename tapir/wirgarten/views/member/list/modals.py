from django.contrib.auth.decorators import permission_required
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.member import (
    CoopShareCancelForm,
    CoopShareTransferForm,
    PersonalDataForm,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.service.member import cancel_coop_shares, transfer_coop_shares
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
            member_id=kwargs["pk"],
            quantity=x.cleaned_data["quantity"],
            cancellation_date=x.cleaned_data["cancellation_date"],
            valid_at=x.cleaned_data["valid_at"],
            actor=request.user,
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
        handler=save_member_and_assign_number,
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:member_list"),
        **kwargs,
    )


def save_member_and_assign_number(member: Member):
    member.save()
    cache = {}
    if not MemberNumberService.assign_member_number_if_eligible(member, cache=cache):
        member.save()  # second save persists keycloak ID (#947)
