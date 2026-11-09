from django.contrib.auth.decorators import permission_required
from django.db import IntegrityError, transaction
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.member import (
    CoopShareCancelForm,
    CoopShareTransferForm,
)
from tapir.wirgarten.forms.member_number import AdminMemberCreationForm
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
        form_class=AdminMemberCreationForm,
        handle_validation_errors=True,
        handler=save_member_and_assign_number,
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:member_list"),
        **kwargs,
    )


def save_member_and_assign_number(form: AdminMemberCreationForm):
    try:
        with transaction.atomic():
            form.instance.username = form.instance.email
            form.instance.member_no = None
            form.save()
            number = form.cleaned_data.get("member_no")
            if number is None:
                MemberNumberService.assign_member_number_if_eligible(
                    form.instance, cache={}, actor=form.request.user
                )
            else:
                MemberNumberService.set_member_number(
                    form.instance, number, actor=form.request.user
                )
            KeycloakUserManager.create_keycloak_user_if_necessary(
                user=form.instance, initial_password=None
            )
    except IntegrityError as error:
        MemberNumberService.raise_if_number_conflict(error)
        raise
