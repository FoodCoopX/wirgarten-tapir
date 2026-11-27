from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from tapir.accounts.services.email_normaliser import EmailNormaliser
from tapir.core.forms import SubscriptionManagementLinkRequestForm
from tapir.core.services.subscription_management_link_sender import (
    SubscriptionManagementLinkSender,
)
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.utils.services.tapir_cache import TapirCache


class SubscriptionManagementView(View):
    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        cache = {}
        address = SubscriptionManagementTokenSigner.get_address(token=token)
        if address is None:
            return render(
                request,
                "core/subscription_management_link_expired.html",
                {"cache": cache},
            )

        member_id = TapirCache.get_member_id_with_main_address(
            address=address, cache=cache
        )
        if member_id is not None:
            return redirect("wirgarten:member_detail", member_id)

        return render(
            request,
            "core/subscription_management.html",
            {"address": address, "cache": cache},
        )


class SubscriptionManagementLinkRequestView(FormView):
    form_class = SubscriptionManagementLinkRequestForm
    template_name = "core/subscription_management_link_request.html"
    success_url = reverse_lazy("core:subscription_management_link_requested")

    def form_valid(self, form: SubscriptionManagementLinkRequestForm) -> HttpResponse:
        SubscriptionManagementLinkSender.send_link(
            address=EmailNormaliser.normalise(form.cleaned_data["email"]), cache={}
        )
        return super().form_valid(form)


class SubscriptionManagementLinkRequestedView(TemplateView):
    template_name = "core/subscription_management_link_requested.html"
