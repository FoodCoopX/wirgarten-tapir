from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from tapir.associations.deposit_forms import (
    DepositAgreementForm,
    DepositMemberChoiceForm,
    DepositReceiptForm,
    DepositRefundForm,
)
from tapir.associations.services.association_deposit_administration_provider import (
    AssociationDepositAdministrationProvider,
)
from tapir.associations.services.association_deposit_agreement_authorizer import (
    AssociationDepositAgreementAuthorizer,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.services.association_deposit_refund_recorder import (
    AssociationDepositRefundRecorder,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today, legal_status_is_association


class DepositAdministrationView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "associations/deposit_administration.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    def get_context_data(self, **kwargs):
        if not legal_status_is_association(cache=self.cache):
            raise Http404
        context = super().get_context_data(**kwargs)
        context.update(cache=self.cache, member_form=DepositMemberChoiceForm())
        if "member_id" not in self.kwargs:
            include_closed = self.request.GET.get("status") == "all"
            context.update(
                include_closed=include_closed,
                accounts=Paginator(
                    AssociationDepositAdministrationProvider.get_accounts(
                        include_closed, self.cache
                    ),
                    50,
                ).get_page(self.request.GET.get("page")),
            )
            return context
        member = get_object_or_404(Member, pk=self.kwargs["member_id"])
        context.update(
            AssociationDepositAdministrationProvider.get_case(member, self.cache)
        )
        account = context["account"]
        today = get_today(self.cache)
        context.setdefault(
            "agreement_form",
            DepositAgreementForm(
                prefix="agreement",
                initial={
                    "amount": account.agreed_amount if account else None,
                    "instalment_count": account.instalment_count if account else 1,
                    "effective_from": today,
                    "consented_on": today,
                    "expected_revision": account.agreement_revision if account else 0,
                },
            ),
        )
        context.setdefault(
            "receipt_form",
            DepositReceiptForm(
                prefix="receipt",
                initial={
                    "received_on": today,
                    "expected_committed_amount": context["details"]["committed_amount"],
                },
            ),
        )
        context.setdefault(
            "refund_form",
            DepositRefundForm(
                prefix="refund",
                initial={
                    "refunded_on": today,
                    "expected_revision": account.agreement_revision if account else 0,
                    "expected_committed_amount": context["details"]["committed_amount"],
                },
            ),
        )
        return context

    def get(self, request, *args, **kwargs):
        if not legal_status_is_association(cache=self.cache):
            raise Http404
        if "member" in request.GET:
            form = DepositMemberChoiceForm(request.GET)
            if form.is_valid():
                return redirect(
                    "associations:deposit_case",
                    member_id=form.cleaned_data["member"].pk,
                )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        if "member" not in context:
            raise Http404
        action = request.POST.get("action")
        if action not in ("agreement", "receipt", "refund"):
            raise Http404
        form = {
            "agreement": DepositAgreementForm,
            "receipt": DepositReceiptForm,
            "refund": DepositRefundForm,
        }[action](request.POST, prefix=action)
        if form.is_valid():
            save = {
                "agreement": AssociationDepositAgreementAuthorizer.authorize_agreement,
                "receipt": AssociationDepositReceiptRecorder.record_received_deposit,
                "refund": AssociationDepositRefundRecorder.record_external_refund,
            }[action]
            try:
                save(
                    member=context["member"],
                    actor=request.user,
                    cache=self.cache,
                    **form.cleaned_data
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                success_message = {
                    "agreement": "Vereinbarung gespeichert.",
                    "refund": "Externe Rückzahlung erfasst; neue Einzüge benötigen eine neue Vereinbarung.",
                    "receipt": "Zahlungseingang erfasst; eine identische Wiederholung wird nicht erneut gebucht.",
                }[action]
                messages.success(request, success_message)
                return redirect(
                    "associations:deposit_case", member_id=context["member"].pk
                )
        context[action + "_form"] = form
        return self.render_to_response(context)
