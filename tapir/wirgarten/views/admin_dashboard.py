import datetime
import json

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, DateField, ExpressionWrapper, F, Max, Sum
from django.db.models.functions import ExtractYear
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.http import require_GET

from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import LEGAL_STATUS_COOPERATIVE
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.wirgarten.models import (
    CoopShareTransaction,
    Member,
    Product,
    QuestionaireCancellationReasonResponse,
    QuestionaireTrafficSourceOption,
    QuestionaireTrafficSourceResponse,
    Subscription,
    WaitingListEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_next_contract_start_date
from tapir.wirgarten.service.payment import (
    get_next_payment_date,
    get_automatically_calculated_solidarity_excess,
    get_total_payment_amount,
)
from tapir.wirgarten.service.products import (
    get_active_product_capacities,
    get_active_product_types,
    get_current_growing_period,
    get_active_and_future_subscriptions,
    get_next_growing_period,
    get_product_price,
    get_free_product_capacity,
)
from tapir.wirgarten.utils import format_currency, format_date, get_today


@require_GET
def get_cashflow_chart_data(request):
    last_contract_end = Subscription.objects.aggregate(max_date=Max("end_date"))[
        "max_date"
    ]

    payment_dates = [get_next_payment_date()]
    while payment_dates[-1] < last_contract_end:
        payment_dates.append(payment_dates[-1] + relativedelta(months=1))

    return JsonResponse(
        {
            "labels": [format_date(x) for x in payment_dates],
            "data": [get_total_payment_amount(x) for x in payment_dates],
        },
        safe=True,
    )


class AdminDashboardView(PermissionRequiredMixin, generic.TemplateView):
    template_name = "wirgarten/admin_dashboard.html"
    permission_required = "coop.view"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_growing_period = get_current_growing_period(cache=self.cache)
        if not current_growing_period:
            context["no_growing_period"] = True
            return context

        base_product_type = BaseProductTypeService.get_base_product_type(
            cache=self.cache
        )
        if base_product_type is None:
            context["no_base_product_type"] = True
            return context
        self.harvest_share_type = base_product_type

        next_contract_start_date = get_next_contract_start_date(cache=self.cache)
        next_growing_period = get_next_growing_period(
            next_contract_start_date, cache=self.cache
        )

        context["next_contract_start_date"] = next_contract_start_date
        context["next_period_start_date"] = (
            next_growing_period.start_date if next_growing_period else None
        )

        self.add_capacity_chart_context(
            context, base_product_type.id, next_contract_start_date
        )
        if next_growing_period:
            self.add_capacity_chart_context(
                context, base_product_type.id, next_growing_period.start_date, "next"
            )
        self.add_traffic_source_questionaire_chart_context(context)
        self.add_cancellation_chart_context(context)
        self.add_cancellation_reasons_chart_context(context)
        self.add_cancelled_coop_shares_context(context)

        context["active_members"] = len(
            list(filter(lambda x: x.coop_shares_quantity > 0, Member.objects.all()))
        )
        context["coop_shares_value"] = format_currency(
            (
                CoopShareTransaction.objects.filter(
                    valid_at__lt=next_contract_start_date
                )
                .aggregate(quantity=Sum("quantity"))
                .get("quantity", 0)
                or 0
            )
            * settings.COOP_SHARE_PRICE
        ).replace(",00", "")

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

        context["solidarity_overplus"] = (
            get_automatically_calculated_solidarity_excess()
        )
        context["status_seperate_coop_shares"] = get_parameter_value(
            ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES, cache=self.cache
        )
        context["status_negative_soli_price_allowed"] = get_parameter_value(
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=self.cache
        )

        today = get_today(cache=self.cache)
        (
            context["harvest_share_variants_data"],
            context["harvest_share_variants_labels"],
        ) = self.get_harvest_share_variants_chart_data(
            Subscription.objects.filter(
                start_date__lte=today,
                end_date__gte=today,
                product__type=self.harvest_share_type,
            )
        )

        context["show_cooperative_content"] = (
            get_parameter_value(
                ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=self.cache
            )
            == LEGAL_STATUS_COOPERATIVE
        )

        return context

    def add_cancelled_coop_shares_context(self, context):
        cancellations = {
            c["year"]: -c["total_quantity"] * settings.COOP_SHARE_PRICE
            for c in (
                CoopShareTransaction.objects.filter(
                    transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
                    valid_at__gte=get_today(cache=self.cache),
                )
                .annotate(year=ExtractYear("valid_at"))
                .values("year")
                .annotate(total_quantity=Sum("quantity"))
                .order_by("year")
            )
        }
        context["cancelled_coop_shares_labels"] = list(cancellations.keys())
        context["cancelled_coop_shares_data"] = list(cancellations.values())

    def add_cancellation_reasons_chart_context(self, context):
        qs = QuestionaireCancellationReasonResponse.objects.filter(
            timestamp__gte=get_today(cache=self.cache) + relativedelta(day=1, years=-1)
        )
        total = qs.count()
        if total == 0:
            context["cancellation_reason_labels"] = []
            context["cancellation_reason_data"] = []
            context["cancellations_other_reasons"] = []
            return

        responses = (
            qs.filter(custom=False).values("reason").annotate(count=Count("reason"))
        )
        custom_responses = list(
            {x.reason: x for x in qs.filter(custom=True).order_by("-timestamp")}.keys()
        )

        context["cancellation_reason_labels"] = list(
            map(lambda x: x["reason"], responses)
        ) + ["Sonstige"]
        context["cancellation_reason_data"] = list(
            map(lambda x: x["count"] / total * 100, responses)
        ) + [len(custom_responses) / total * 100]

        context["cancellations_other_reasons"] = custom_responses

    def add_cancellation_chart_context(self, context):
        month_labels = [
            get_today(cache=self.cache) + relativedelta(day=1, months=-i + 1)
            for i in range(13)
        ][::-1]

        cancellations_data = [
            {"label": "Probeverträge", "data": [0] * 13},
            {"label": "Gekündigte Verträge", "data": [0] * 13},
        ]

        for index, month in enumerate(month_labels):
            start_of_month = month

            # Calculate the total number of subscriptions in trial - cancelled for this month
            trial_cancelled_count = (
                Subscription.objects.filter(start_date=start_of_month)
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

            # Calculate the total number of new subscriptions for this month
            total_count = Subscription.objects.filter(
                start_date=start_of_month,
            ).count()

            cancellations_data[0]["data"][index] = total_count
            cancellations_data[1]["data"][index] = trial_cancelled_count

        # Format the month values
        cancellations_labels = [month.strftime("%m/%y") for month in month_labels]

        # Set the context variables
        context["cancellations_data"] = json.dumps(cancellations_data)
        context["cancellations_labels"] = cancellations_labels

    def add_capacity_chart_context(
        self,
        context,
        base_type_id,
        reference_date=None,
        prefix="current",
    ):
        if reference_date is None:
            reference_date = get_next_contract_start_date(cache=self.cache)

        active_product_capacities = {
            c.product_type.id: c
            for c in get_active_product_capacities(reference_date, cache=self.cache)
        }

        KEY_CAPACITY_LINKS = prefix + "_capacity_links"
        KEY_CAPACITY_LABELS = prefix + "_capacity_labels"
        KEY_USED_CAPACITY = prefix + "_used_capacity"
        KEY_FREE_CAPACITY = prefix + "_free_capacity"

        context[KEY_CAPACITY_LINKS] = []
        context[KEY_CAPACITY_LABELS] = []
        context[KEY_USED_CAPACITY] = []
        context[KEY_FREE_CAPACITY] = []

        sorted_product_capacities = sorted(
            active_product_capacities.values(),
            key=lambda c: c.product_type_id == base_type_id,
            reverse=True,
        )

        for product_capacity in sorted_product_capacities:
            product_type = product_capacity.product_type

            total_capacity = (
                float(product_capacity.capacity) or 1
            )  # "or 1" to avoid a division by 0

            free_capacity = get_free_product_capacity(
                product_type.id, reference_date, cache=self.cache
            )
            used_capacity = total_capacity - free_capacity

            context[KEY_USED_CAPACITY].append(used_capacity / total_capacity * 100)
            context[KEY_FREE_CAPACITY].append(free_capacity / total_capacity * 100)
            context[KEY_CAPACITY_LINKS].append(
                f"{reverse_lazy('wirgarten:product')}?periodId={product_capacity.period.id}&capacityId={product_capacity.id}"
            )
            base_product = Product.objects.filter(
                type=product_capacity.product_type, base=True
            ).first()

            base_share_size = float(
                get_product_price(base_product, reference_date, cache=self.cache).size
            )

            free_share_count = round(free_capacity / base_share_size, 2)
            used_share_count = round(used_capacity / base_share_size, 2)

            context[KEY_CAPACITY_LABELS].append(
                [
                    product_type.name,
                    f"{used_share_count} Anteile vergeben",
                    (
                        (f"{free_share_count} Anteile noch frei")
                        if free_share_count > 0
                        else "Keine Anteile mehr frei"
                    ),
                ],
            )

    def add_traffic_source_questionaire_chart_context(self, context):
        month_labels = [
            get_today(cache=self.cache) + relativedelta(day=1, months=-i)
            for i in range(13)
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
            pt["name"]: 0
            for pt in get_active_product_types(cache=self.cache).values("name")
        }
        contract_types.update(
            {
                x["product__type__name"]: x["member_count"]
                for x in get_active_and_future_subscriptions(cache=self.cache)
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
            - contract_types.get(self.harvest_share_type.name, 0)
        )
        return contract_data, contract_labels
