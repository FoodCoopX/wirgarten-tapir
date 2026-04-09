import json

from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Max, Sum
from django.db.models.functions import ExtractYear
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.http import require_GET

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.product_type_lowest_free_capacity_after_date_generic import (
    ProductTypeLowestFreeCapacityAfterDateCalculator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.models import (
    CoopShareTransaction,
    Member,
    OrderFeedback,
    QuestionaireCancellationReasonResponse,
    QuestionaireTrafficSourceOption,
    QuestionaireTrafficSourceResponse,
    Subscription,
    Payment,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    annotate_member_queryset_with_coop_shares_total_value,
)
from tapir.wirgarten.service.payment import (
    get_next_payment_date,
)
from tapir.wirgarten.service.products import (
    get_active_product_capacities,
    get_active_product_types,
    get_active_and_future_subscriptions,
    get_next_growing_period,
    get_product_price,
)
from tapir.wirgarten.utils import (
    format_currency,
    format_date,
    get_today,
    legal_status_is_cooperative,
    legal_status_is_association,
)


@require_GET
def get_cashflow_chart_data(request):
    cache = {}
    last_contract_end = Subscription.objects.aggregate(max_date=Max("end_date"))[
        "max_date"
    ]

    payment_dates = [get_next_payment_date(cache=cache)]
    while payment_dates[-1] < last_contract_end:
        payment_dates.append(payment_dates[-1] + relativedelta(months=1))

    generated_payments = set()
    monthly_sums = []
    all_payments = Payment.objects.all()
    for payment_date in payment_dates:
        generated_payments_for_this_month = (
            MonthPaymentBuilder.build_payments_for_month(
                reference_date=payment_date,
                cache=cache,
                generated_payments=generated_payments,
            )
        )
        generated_payments.update(generated_payments_for_this_month)

        sum_for_this_month = sum(
            [payment.amount for payment in generated_payments_for_this_month]
        ) + sum(
            [
                payment.amount
                for payment in all_payments
                if payment.due_date.year == payment_date.year
                and payment.due_date.month == payment_date.month
            ]
        )
        monthly_sums.append(sum_for_this_month)

    return JsonResponse(
        {
            "labels": [format_date(x) for x in payment_dates],
            "data": monthly_sums,
        },
        safe=True,
    )


def get_recent_feedbacks(limit: int = 10):
    return list(
        OrderFeedback.objects.order_by("-created_at")[:limit].values(
            "feedback_text",
            "created_at",
            "member__first_name",
            "member__last_name",
            "member__email",
            "member__phone_number",
            "member__pk"
        )
    )


class AdminDashboardView(PermissionRequiredMixin, generic.TemplateView):
    template_name = "wirgarten/admin_dashboard.html"
    permission_required = "coop.view"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_growing_period = TapirCache.get_growing_period_at_date(
            reference_date=get_today(cache=self.cache), cache=self.cache
        )
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

        next_contract_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=self.cache),
                apply_buffer_time=True,
                cache=self.cache,
            )
        )
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
        self.add_cancelled_association_memberships_context(context)

        members_with_shares = annotate_member_queryset_with_coop_shares_total_value(
            Member.objects.all(), cache=self.cache
        ).filter(coop_shares_total_value__gt=0)
        context["active_members"] = members_with_shares.count()
        context["coop_shares_value"] = format_currency(
            (
                CoopShareTransaction.objects.filter(
                    valid_at__lt=next_contract_start_date
                )
                .aggregate(quantity=Sum("quantity"))
                .get("quantity", 0)
                or 0
            )
            * get_parameter_value(ParameterKeys.COOP_SHARE_PRICE, cache=self.cache)
        ).replace(",00", "")

        context["cancellations_during_trial"] = len(
            Subscription.objects.filter(cancellation_ts__isnull=False)
        )
        context["recent_feedbacks"] = get_recent_feedbacks()

        context["solidarity_overplus"] = SolidarityValidator.get_solidarity_excess(
            reference_date=get_today(cache=self.cache), cache=self.cache
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

        context["show_cooperative_content"] = legal_status_is_cooperative(
            cache=self.cache
        )
        context["show_association_content"] = legal_status_is_association(
            cache=self.cache
        )

        return context

    def add_cancelled_coop_shares_context(self, context):
        cancellations = {
            c["year"]: -c["total_quantity"]
            * get_parameter_value(ParameterKeys.COOP_SHARE_PRICE, cache=self.cache)
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

    def add_cancelled_association_memberships_context(self, context):
        cancellations_per_year = {}
        for cancelled_membership in Subscription.objects.filter(
            product__type__is_association_membership=True, end_date__isnull=False
        ).order_by("end_date"):
            if cancelled_membership.end_date.year not in cancellations_per_year.keys():
                cancellations_per_year[cancelled_membership.end_date.year] = 0
            cancellations_per_year[cancelled_membership.end_date.year] += 1

        context["cancelled_association_memberships_labels"] = list(
            cancellations_per_year.keys()
        )
        context["cancelled_association_memberships_data"] = list(
            cancellations_per_year.values()
        )

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

        context["cancellation_reason_labels"] = [
            response["reason"] for response in responses
        ] + ["Sonstige"]

        context["cancellation_reason_data"] = [
            response["count"] / total * 100 for response in responses
        ] + [len(custom_responses) / total * 100]

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
            cancelled_subscriptions = Subscription.objects.filter(
                cancellation_ts__isnull=False,
                cancellation_ts__year=month.year,
                cancellation_ts__month=month.month,
            )
            subscriptions_cancelled_while_in_trial = list(
                filter(
                    lambda subscription: TrialPeriodManager.is_contract_in_trial(
                        subscription,
                        reference_date=subscription.cancellation_ts.date(),
                        cache=self.cache,
                    ),
                    cancelled_subscriptions,
                )
            )
            trial_cancelled_count = len(subscriptions_cancelled_while_in_trial)

            total_count = cancelled_subscriptions.count()

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
            reference_date = get_first_of_next_month(date=get_today(cache=self.cache))

        active_product_capacities = {
            c.product_type_id: c
            for c in get_active_product_capacities(
                reference_date, cache=self.cache
            ).select_related("period", "product_type")
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

            free_capacity = ProductTypeLowestFreeCapacityAfterDateCalculator.get_lowest_free_capacity_after_date(
                product_type=product_type,
                reference_date=reference_date,
                cache=self.cache,
            )
            used_capacity = total_capacity - free_capacity

            context[KEY_USED_CAPACITY].append(used_capacity / total_capacity * 100)
            context[KEY_FREE_CAPACITY].append(free_capacity / total_capacity * 100)
            context[KEY_CAPACITY_LINKS].append(
                f"{reverse_lazy('wirgarten:product')}?periodId={product_capacity.period.id}&capacityId={product_capacity.id}"
            )
            base_product = TapirCache.get_base_product_by_product_type_id(
                product_type_id=product_capacity.product_type_id, cache=self.cache
            )

            product_price = get_product_price(
                base_product, reference_date, cache=self.cache
            )
            base_share_size = (
                float(product_price.size) if product_price is not None else 1
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
