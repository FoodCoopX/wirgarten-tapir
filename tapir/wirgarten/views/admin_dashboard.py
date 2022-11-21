from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Sum
from django.views import generic

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import (
    Member,
    Subscription,
    HarvestShareProduct,
    ProductPrice,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.payment import (
    get_next_payment_date,
    get_total_payment_amount,
    get_solidarity_overplus,
)
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_active_product_capacities,
    get_future_subscriptions,
)


def format_currency(number):
    format_str = "{{:,.{}f}}".format(2)
    number_str = format_str.format(number)
    return number_str.replace(",", "X").replace(".", ",").replace("X", ".")


HARVEST_SHARES_PRODUCT_TYPE_NAME = (
    "Ernteanteile"  # FIXME: the name should be configurable somewhere
)


class AdminDashboardView(PermissionRequiredMixin, generic.TemplateView):
    template_name = "wirgarten/admin_dashboard.html"
    permission_required = "coop.admin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        harvest_share_type = get_active_product_types().get(
            name=HARVEST_SHARES_PRODUCT_TYPE_NAME
        )

        harvest_share_capacity = get_active_product_capacities().get(
            product_type=harvest_share_type
        )
        active_harvest_share_subs = get_future_subscriptions().filter(
            product__type=harvest_share_type
        )

        # FIXME: these queries are not perfect yet

        # sum without solidarity_price
        context["harvest_shares_used"] = sum(
            map(
                lambda x: x.quantity
                * float(
                    ProductPrice.objects.filter(product=x.product)
                    .order_by("-valid_from")
                    .first()
                    .price
                ),
                active_harvest_share_subs,
            )
        )
        context["harvest_shares_free"] = (
            float(harvest_share_capacity.capacity) - context["harvest_shares_used"]
        )
        context["harvest_shares_used_percent"] = round(
            context["harvest_shares_used"]
            / (context["harvest_shares_used"] + context["harvest_shares_free"])
            * 100,
            1,
        )
        base_variant_price = float(
            ProductPrice.objects.filter(
                product=HarvestShareProduct.objects.get(
                    type=harvest_share_type, name="M"
                )
            )
            .first()
            .price
        )
        context["harvest_shares_m_equivalents"] = round(
            context["harvest_shares_free"] / base_variant_price
        )

        context["active_members"] = len(Member.objects.all())
        context["cancellations_during_trial"] = len(
            Subscription.objects.filter(cancellation_ts__isnull=False)
        )
        context[
            "waiting_list_coop_shares"
        ] = 0  # FIXME: add as soon as we have the waiting list
        context[
            "waiting_list_harvest_shares"
        ] = 0  # FIXME: add as soon as we have the waiting list
        context["next_payment_date"] = get_next_payment_date()
        context["next_payment_amount"] = format_currency(
            get_total_payment_amount(context["next_payment_date"])
        )
        context["solidarity_overplus"] = format_currency(get_solidarity_overplus())
        context["status_seperate_coop_shares"] = get_parameter_value(
            Parameter.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES
        )
        context["status_negative_soli_price_allowed"] = get_parameter_value(
            Parameter.HARVEST_NEGATIVE_SOLIPRICE_ENABLED
        )

        (
            context["contract_distribution_data"],
            context["contract_distribution_labels"],
        ) = self.get_contract_distribution_chart_data(context)

        (
            context["harvest_share_variants_data"],
            context["harvest_share_variants_labels"],
        ) = self.get_harvest_share_variants_chart_data(active_harvest_share_subs)

        return context

    def get_harvest_share_variants_chart_data(self, active_harvest_share_subs):
        variant_labels = []
        variant_data = []
        for x in active_harvest_share_subs.values("product__name").annotate(
            count=Sum("quantity")
        ):
            variant_labels.append(x["product__name"] + "-Anteile")
            variant_data.append(x["count"])
        return variant_data, variant_labels

    def get_contract_distribution_chart_data(self, context):
        contract_types = {
            pt["name"]: 0 for pt in get_active_product_types().values("name")
        }
        contract_types.update(
            {
                x["product__type__name"]: x["member_count"]
                for x in get_future_subscriptions()
                .values("product__type__name")
                .annotate(member_count=Count("member_id", distinct=True))
                .order_by("-member_count")
            }
        )
        contract_labels = ["Alle Mitglieder"]
        contract_data = [context["active_members"]]
        for k, v in sorted(contract_types.items(), key=lambda item: -item[1]):
            contract_labels.append(k)
            contract_data.append(v)
        contract_labels.append("nur Geno-Anteile")
        contract_data.append(
            context["active_members"]
            - contract_types.get(HARVEST_SHARES_PRODUCT_TYPE_NAME, 0)
        )
        return contract_data, contract_labels
