from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import CoopShareTransaction, Subscription
from tapir.wirgarten.parameters import Parameter


class NewContractsView(PermissionRequiredMixin, TemplateView):
    # Display a list of all new contracts that are not confirmed by the admin yet

    template_name = "wirgarten/subscription/new_contracts_overview.html"
    permission_required = "accounts.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        coop_shares = CoopShareTransaction.objects.filter(
            admin_confirmed__isnull=True,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        ).order_by("timestamp")

        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        harvest_shares = Subscription.objects.filter(
            admin_confirmed__isnull=True, product__type_id=base_product_type_id
        ).order_by("created_at")

        additional_shares = (
            Subscription.objects.filter(admin_confirmed__isnull=True)
            .exclude(product__type_id=base_product_type_id)
            .order_by("created_at")
        )

        context["new_harvest_and_coop_shares"] = harvest_shares
        context["new_coop_shares"] = coop_shares
        context["new_additional_shares"] = additional_shares
        return context


@permission_required("accounts.manage")
@transaction.atomic
def confirm_new_contracts(request, **kwargs):
    query_dict = dict(x.split("=") for x in request.environ["QUERY_STRING"].split("&"))
    for key, val in query_dict.items():
        query_dict[key] = val.split(",")

    harvest_and_coop_shares = query_dict.pop("new_harvest_and_coop_shares", [])
    additional_shares = query_dict.pop("new_additional_shares", [])
    subscription_ids = harvest_and_coop_shares + additional_shares
    now = timezone.now()
    if len(subscription_ids):
        Subscription.objects.filter(id__in=subscription_ids).update(admin_confirmed=now)

    coop_shares = query_dict.pop("new_coop_shares", [])
    if len(coop_shares):
        CoopShareTransaction.objects.filter(id__in=coop_shares).update(
            admin_confirmed=now
        )

    return HttpResponseRedirect(reverse_lazy("wirgarten:new_contracts"))
