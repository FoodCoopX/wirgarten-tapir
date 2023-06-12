import datetime
import itertools
import json
from datetime import date
from math import floor

from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Sum, F, DateField, ExpressionWrapper
from django.urls import reverse_lazy
from django.views import generic

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.models import (
    Member,
    Subscription,
    WaitingListEntry,
    Product,
    QuestionaireTrafficSourceOption,
    QuestionaireTrafficSourceResponse,
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
    get_product_price,
    get_next_growing_period,
)
from tapir.wirgarten.utils import format_currency


class AdminDashboardView(PermissionRequiredMixin, generic.TemplateView):
    template_name = "wirgarten/admin_dashboard.html"
    permission_required = "coop.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        harvest_share_type = get_active_product_types().get(
            name=ProductTypes.HARVEST_SHARES
        )

        self.add_capacity_chart_context(context)
        self.add_capacity_chart_context(
            context, get_next_growing_period().start_date, "next"
        )
        self.add_traffic_source_questionaire_chart_context(context)
        self.add_cancellation_chart_context(context)

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

        active_subs = get_future_subscriptions().order_by("-product__type")
        (
            context["harvest_share_variants_data"],
            context["harvest_share_variants_labels"],
        ) = self.get_harvest_share_variants_chart_data(
            active_subs.filter(product__type=harvest_share_type)
        )

        return context

    def add_cancellation_chart_context(self, context):
        month_labels = [
            date.today() + relativedelta(day=1, months=-i) for i in range(13)
        ][::-1]
        date_cutoff = date.today() + relativedelta(day=1, months=-13)

        cancellations_data = [
            {"label": "Probeverträge", "data": [0] * 13},
            {"label": "Gekündigte Verträge", "data": [0] * 13},
        ]

        for index, month in enumerate(month_labels):
            start_of_month = month
            end_of_month = month + relativedelta(months=1) - relativedelta(days=1)

            # Calculate the total number of subscriptions in trial - cancelled for this month
            trial_cancelled_count = (
                Subscription.objects.filter(
                    created_at__gte=start_of_month, created_at__lte=end_of_month
                )
                .exclude(cancellation_ts=None)
                .annotate(
                    trial_end_date=ExpressionWrapper(
                        F("start_date") + datetime.timedelta(days=30),
                        output_field=DateField(),
                    )
                )
                .filter(cancellation_ts__lte=F("trial_end_date"))
                .count()
            )

            # Calculate the total number of cancelled subscriptions for this month
            cancelled_count = Subscription.objects.filter(
                cancellation_ts__gte=start_of_month, cancellation_ts__lte=end_of_month
            ).count()

            cancellations_data[0]["data"][index] = trial_cancelled_count
            cancellations_data[1]["data"][index] = cancelled_count

        # Format the month values
        cancellations_labels = [month.strftime("%m/%y") for month in month_labels]

        # Set the context variables
        context["cancellations_data"] = json.dumps(cancellations_data)
        context["cancellations_labels"] = cancellations_labels

    def add_capacity_chart_context(
        self, context, reference_date=date.today(), prefix="current"
    ):
        active_capacities = {
            c.product_type.id: c for c in get_active_product_capacities(reference_date)
        }
        active_subs = get_future_subscriptions(reference_date).order_by(
            "-product__type"
        )

        KEY_CAPACITY_LINKS = prefix + "_capacity_links"
        KEY_CAPACITY_LABELS = prefix + "_capacity_labels"
        KEY_USED_CAPACITY = prefix + "_used_capacity"
        KEY_FREE_CAPACITY = prefix + "_free_capacity"

        context[KEY_CAPACITY_LINKS] = []
        context[KEY_CAPACITY_LABELS] = []
        context[KEY_USED_CAPACITY] = []
        context[KEY_FREE_CAPACITY] = []

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
                    lambda x: x.quantity * float(get_product_price(x.product).price),
                    subs,
                )
            )
            context[KEY_USED_CAPACITY].append(used / total * 100)
            context[KEY_FREE_CAPACITY].append(100 - (used / total * 100))
            context[KEY_CAPACITY_LINKS].append(
                f"{reverse_lazy('wirgarten:product')}?periodId={capacity.period.id}&capacityId={capacity.id}"
            )
            # TODO: generify, no hardcoded product names!
            if product_type.name == ProductTypes.HARVEST_SHARES:
                base_share_value = get_product_price(
                    Product.objects.get(
                        type__name=ProductTypes.HARVEST_SHARES, base=True
                    )
                ).price
            elif product_type.name == ProductTypes.CHICKEN_SHARES:
                base_share_value = get_product_price(
                    Product.objects.get(
                        type__name=ProductTypes.CHICKEN_SHARES, base=True
                    )
                ).price
            elif product_type.name == ProductTypes.CHICKEN_SHARES:
                base_share_value = get_product_price(
                    Product.objects.get(type__name=ProductTypes.BESTELLCOOP, base=True)
                ).price

            if base_share_value:
                base_share_count = floor((total - used) / float(base_share_value))

            context[KEY_CAPACITY_LABELS].append(
                [
                    product_type.name,
                    f"{base_share_count} Anteile verfügbar"
                    if base_share_count
                    else None,
                    f"{format_currency(total - used)} €",
                ]
            )

    def add_traffic_source_questionaire_chart_context(self, context):
        month_labels = [
            date.today() + relativedelta(day=1, months=-i) for i in range(13)
        ][::-1]

        # Create an additional queryset for "No Response"
        no_response = QuestionaireTrafficSourceOption(name="Keine Angabe")

        # Combine actual options and "No Response"
        options = list(QuestionaireTrafficSourceOption.objects.all()) + [no_response]

        output = []

        for option in options:
            option_data = {
                "label": option.name,
                "data": [0]
                * 13,  # Initialize data with zeros for each of the 13 months
            }

            for index, month in enumerate(month_labels):
                if option != no_response:
                    response_count = (
                        QuestionaireTrafficSourceResponse.objects.filter(
                            sources=option,
                            timestamp__month=month.month,
                            timestamp__year=month.year,
                        )
                        .distinct()
                        .count()
                    )
                else:
                    response_count = (
                        Member.objects.filter(
                            created_at__month=month.month, created_at__year=month.year
                        )
                        .exclude(
                            id__in=QuestionaireTrafficSourceResponse.objects.filter(
                                timestamp__month=month.month, timestamp__year=month.year
                            )
                            .distinct()
                            .values_list("member_id", flat=True)
                        )
                        .count()
                    )

                option_data["data"][index] = response_count

            output.append(option_data)

        # Calculate the total responses per month
        total_responses_per_month = [
            sum(option["data"][index] for option in output)
            for index in range(len(month_labels))
        ]

        # Convert the counts to percentages
        for option_data in output:
            for index, response_count in enumerate(option_data["data"]):
                total_responses_in_month = total_responses_per_month[index]
                percentage = (
                    round((response_count / total_responses_in_month) * 100, 2)
                    if total_responses_in_month > 0
                    else 0
                )
                option_data["data"][index] = percentage

        # Format the month values
        traffic_source_labels = [month.strftime("%m/%y") for month in month_labels]

        # Set the context variables
        context["traffic_source_data"] = json.dumps(output)
        context["traffic_source_labels"] = traffic_source_labels

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
