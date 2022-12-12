import itertools
from datetime import date

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Sum
from django.urls import reverse_lazy
from django.views import generic

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.models import (
    Member,
    Subscription,
    ProductPrice,
    WaitingListEntry,
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


class AdminDashboardView(PermissionRequiredMixin, generic.TemplateView):
    template_name = "wirgarten/admin_dashboard.html"
    permission_required = "coop.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        harvest_share_type = get_active_product_types().get(
            name=ProductTypes.HARVEST_SHARES
        )

        active_capacities = {
            c.product_type.id: c for c in get_active_product_capacities()
        }

        active_subs = get_future_subscriptions().order_by("-product__type")

        today = date.today()

        context["capacity_links"] = []
        context["capacity_labels"] = []
        context["used_capacity"] = []
        context["free_capacity"] = []

        pt_to_subs = {
            product_type.id: list(subs)
            for product_type, subs in itertools.groupby(
                active_subs, key=lambda x: x.product.type
            )
        }
        for capacity in sorted(
            active_capacities.values(),
            key=lambda c: c.product_type.name == ProductTypes.HARVEST_SHARES,
            reverse=True,
        ):
            product_type = capacity.product_type
            subs = pt_to_subs.get(product_type.id, [])

            total = float(capacity.capacity)
            used = sum(
                map(
                    lambda x: x.quantity
                    * float(
                        ProductPrice.objects.filter(
                            product=x.product, valid_from__lte=today
                        )
                        .order_by("-valid_from")
                        .first()
                        .price
                    ),
                    subs,
                )
            )
            context["used_capacity"].append(used / total * 100)
            context["free_capacity"].append(100 - (used / total * 100))
            context["capacity_links"].append(
                f"{reverse_lazy('wirgarten:product')}?periodId={capacity.period.id}&capacityId={capacity.id}"
            )
            # TODO: show free capacity as quantity of base product shares
            context["capacity_labels"].append(
                [product_type.name, f"{format_currency(total - used)} € frei"]
            )

        context["active_members"] = len(Member.objects.all())
        context["cancellations_during_trial"] = len(
            Subscription.objects.filter(cancellation_ts__isnull=False)
        )

        waiting_list_counts = {
            r["type"]: r["count"]
            for r in WaitingListEntry.objects.all()
            .values("type")
            .annotate(count=Count("type"))
        }

        context["waiting_list_coop_shares"] = waiting_list_counts.get(
            WaitingListEntry.WaitingListType.COOP_SHARES, 0
        )
        context["waiting_list_harvest_shares"] = waiting_list_counts.get(
            WaitingListEntry.WaitingListType.HARVEST_SHARES, 0
        )
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
        context["status_bestellcoop_allowed"] = get_parameter_value(
            Parameter.BESTELLCOOP_SUBSCRIBABLE
        )
        context["status_chickenshares_allowed"] = get_parameter_value(
            Parameter.CHICKEN_SHARES_SUBSCRIBABLE
        )

        (
            context["contract_distribution_data"],
            context["contract_distribution_labels"],
        ) = self.get_contract_distribution_chart_data(context)

        (
            context["harvest_share_variants_data"],
            context["harvest_share_variants_labels"],
        ) = self.get_harvest_share_variants_chart_data(
            active_subs.filter(product__type=harvest_share_type)
        )

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
            - contract_types.get(ProductTypes.HARVEST_SHARES, 0)
        )
        return contract_data, contract_labels
