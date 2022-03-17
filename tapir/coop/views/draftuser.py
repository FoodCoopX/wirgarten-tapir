from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.datetime_safe import date
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_GET

from tapir import settings
from tapir.coop import pdfs
from tapir.coop.forms import (
    DraftUserLimitedForm,
    DraftUserFullForm,
)
from tapir.coop.models import (
    DraftUser,
    ShareOwner,
    ShareOwnership,
    COOP_SHARE_PRICE,
)
from tapir.coop.pdfs import get_membership_agreement_pdf
from tapir.settings import FROM_EMAIL_MEMBER_OFFICE
from tapir.utils.models import copy_user_info, copy_payment_data


class DraftUserViewMixin:
    model = DraftUser
    form_class = DraftUserFullForm


class DraftUserListView(PermissionRequiredMixin, DraftUserViewMixin, generic.ListView):
    permission_required = "coop.manage"


class DraftUserCreateView(
    PermissionRequiredMixin, DraftUserViewMixin, generic.CreateView
):
    permission_required = "coop.manage"

    def form_valid(self, form):
        draft_user = form.instance

        with translation.override(draft_user.preferred_language):
            mail = EmailMessage(
                subject=_("Welcome at %(organisation_name)s!")
                % {"organisation_name": settings.COOP_NAME},
                body=render_to_string(
                    [
                        "coop/email/membership_confirmation_welcome.html",
                        "coop/email/membership_confirmation_welcome.default.html",
                    ],
                    {
                        "owner": draft_user,
                        "contact_email_address": settings.EMAIL_ADDRESS_MEMBER_OFFICE,
                    },
                ),
                from_email=FROM_EMAIL_MEMBER_OFFICE,
                to=[draft_user.email],
                attachments=[
                    (
                        "Beteiligungserklärung %s.pdf" % draft_user.get_display_name(),
                        get_membership_agreement_pdf(draft_user).write_pdf(),
                        "application/pdf",
                    )
                ],
            )
            mail.content_subtype = "html"
            mail.send()


class DraftUserRegisterView(DraftUserViewMixin, generic.CreateView):
    form_class = DraftUserLimitedForm
    success_url = "/coop/user/draft/register/confirm"

    def get_template_names(self):
        return [
            "coop/draftuser_register_form.html",
            "coop/draftuser_register_form.default.html",
        ]


class DraftUserConfirmRegistrationView(DraftUserViewMixin, generic.TemplateView):
    template_name = "coop/draftuser_confirm_registration.html"


class DraftUserUpdateView(
    PermissionRequiredMixin, DraftUserViewMixin, generic.UpdateView
):
    permission_required = "coop.manage"


class DraftUserDetailView(
    PermissionRequiredMixin, DraftUserViewMixin, generic.DetailView
):
    permission_required = "coop.manage"


class DraftUserDeleteView(
    PermissionRequiredMixin, DraftUserViewMixin, generic.DeleteView
):
    permission_required = "coop.manage"
    success_url = reverse_lazy("coop:draftuser_list")


@require_GET
@permission_required("coop.manage")
def draftuser_membership_agreement(request, pk):
    draft_user = get_object_or_404(DraftUser, pk=pk)
    filename = "Beteiligungserklärung %s %s.pdf" % (
        draft_user.first_name,
        draft_user.last_name,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'filename="{}"'.format(filename)
    response.write(pdfs.get_membership_agreement_pdf(draft_user).write_pdf())
    return response


@require_POST
@csrf_protect
@permission_required("coop.manage")
def mark_signed_membership_agreement(request, pk):
    u = DraftUser.objects.get(pk=pk)
    u.signed_membership_agreement = True
    u.save()

    return redirect(u)


@require_POST
@csrf_protect
@permission_required("coop.manage")
def mark_attended_welcome_session(request, pk):
    u = DraftUser.objects.get(pk=pk)
    u.attended_welcome_session = True
    u.save()

    return redirect(u)


@require_POST
@csrf_protect
@permission_required("coop.manage")
def register_draftuser_payment(request, pk):
    draft = get_object_or_404(DraftUser, pk=pk)
    draft.paid_membership_fee = True
    draft.save()
    return redirect(draft.get_absolute_url())


@require_POST
@csrf_protect
@permission_required("coop.manage")
def create_share_owner_from_draft_user_view(request, pk):
    # For now, we don't create users for our new members yet but only ShareOwners. Later, this will be used for
    # investing members

    draft = DraftUser.objects.get(pk=pk)
    if not draft.signed_membership_agreement:
        # TODO(Leon Handreke): Error message
        return redirect(draft)

    if draft.num_shares < 0:
        raise ValidationError(
            "Trying to create a share owner from a draft user without shares"
        )

    with transaction.atomic():
        share_owner = create_share_owner_and_shares_from_draft_user(draft)
        draft.delete()

    return redirect(share_owner.get_absolute_url())


def create_share_owner_and_shares_from_draft_user(draft_user: DraftUser) -> ShareOwner:
    share_owner = ShareOwner.objects.create(
        is_company=False,
        is_investing=draft_user.is_investing,
        ratenzahlung=draft_user.ratenzahlung,
        attended_welcome_session=draft_user.attended_welcome_session,
        paid_membership_fee=draft_user.paid_membership_fee,
    )

    copy_user_info(draft_user, share_owner)
    copy_payment_data(draft_user, share_owner)
    share_owner.save()

    for _ in range(0, draft_user.num_shares):
        ShareOwnership.objects.create(
            owner=share_owner,
            start_date=date.today(),
            amount_paid=(COOP_SHARE_PRICE if draft_user.paid_shares else 0),
        )

    return share_owner
