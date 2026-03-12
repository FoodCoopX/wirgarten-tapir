from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.member import (
    CancellationReasonForm,
    PersonalDataForm,
    SubscriptionRenewalForm,
    WaitingListForm,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    QuestionaireCancellationReasonResponse,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.service.member import (
    create_wait_list_entry,
)
from tapir.wirgarten.service.products import (
    get_next_growing_period,
)
from tapir.wirgarten.utils import (
    check_permission_or_self,
    get_now,
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

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.MEMBERAREA_CHANGE_DATA,
                recipient_id_in_base_queryset=member.id,
            ),
        )

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
def get_coop_shares_waiting_list_form(request, **kwargs):
    member = None
    if request.user and Member.objects.filter(id=request.user.id).exists():
        member = request.user
        kwargs["initial"] = {
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "phone_number": request.user.phone_number,
            "street": request.user.street,
            "street_2": request.user.street_2,
            "postcode": request.user.postcode,
            "city": request.user.city,
        }

    return get_form_modal(
        request=request,
        form_class=WaitingListForm,
        handler=lambda x: create_wait_list_entry(
            first_name=x.cleaned_data["first_name"],
            last_name=x.cleaned_data["last_name"],
            email=x.cleaned_data["email"],
            phone_number=x.cleaned_data["phone_number"],
            street=x.cleaned_data["street"],
            street_2=x.cleaned_data["street_2"],
            postcode=x.cleaned_data["postcode"],
            city=x.cleaned_data["city"],
            member=member,
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

        SubscriptionChangeLogEntry().populate_subscription_changed(
            actor=request.user,
            user=member,
            change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.RENEWED,
            subscriptions=list(form.subs),
            admin_confirmed=get_now(),
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
