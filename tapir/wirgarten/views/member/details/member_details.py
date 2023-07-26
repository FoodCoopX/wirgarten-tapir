from dateutil.relativedelta import relativedelta
from django.db.models import (
    Sum,
    F,
)
from django.utils.translation import gettext_lazy as _
from django.views import generic
from tapir.accounts.models import EmailChangeRequest
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import (
    ProductTypes,
    Permission,
)
from tapir.wirgarten.models import (
    Member,
    Subscription,
    GrowingPeriod,
    WaitingListEntry,
    CoopShareTransaction,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import (
    generate_future_deliveries,
)
from tapir.wirgarten.service.member import (
    get_subscriptions_in_trial_period,
    get_next_contract_start_date,
)
from tapir.wirgarten.service.payment import (
    get_active_subscriptions_grouped_by_product_type,
)
from tapir.wirgarten.service.products import (
    get_active_product_types,
    is_harvest_shares_available,
    get_future_subscriptions,
    is_chicken_shares_available,
    is_bestellcoop_available,
    get_next_growing_period,
    get_active_subscriptions,
)
from tapir.wirgarten.utils import format_date, get_today
from tapir.wirgarten.views.member.list.member_payments import (
    generate_future_payments,
    get_previous_payments,
)
from tapir.wirgarten.views.mixin import PermissionOrSelfRequiredMixin


class MemberDetailView(PermissionOrSelfRequiredMixin, generic.DetailView):
    model = Member
    template_name = "wirgarten/member/member_detail.html"
    permission_required = Permission.Accounts.VIEW

    def get_user_pk(self):
        return self.kwargs["pk"]

    def get_context_data(self, **kwargs):
        context = super(MemberDetailView, self).get_context_data()

        today = kwargs.get("start_date", get_today())
        next_month = today + relativedelta(months=1, day=1)

        context["object"] = self.object
        context["subscriptions"] = get_active_subscriptions_grouped_by_product_type(
            self.object, today
        )

        context["sub_quantities"] = {
            k: sum(map(lambda x: x.quantity, v))
            for k, v in context["subscriptions"].items()
        }
        context["sub_totals"] = {
            k: sum(map(lambda x: x.total_price(), v))
            for k, v in context["subscriptions"].items()
        }

        product_types = get_active_product_types()
        for pt in product_types:
            if pt.name not in context["subscriptions"]:
                context["subscriptions"][pt.name] = []
                context["sub_quantities"][pt.name] = 0

        share_ownerships = list(
            CoopShareTransaction.objects.filter(member=self.object).order_by(
                "timestamp"
            )
        )
        context["coop_shares"] = share_ownerships

        context["coop_shares_total"] = self.object.coop_shares_quantity

        additional_products_available = (
            get_future_subscriptions()
            .filter(
                member_id=self.object.id,
                end_date__gt=get_next_contract_start_date(),
                product__type_id=get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE),
            )
            .exists()
        )

        # FIXME: we need to get rid of the hardcoded product types...
        context["available_product_types"] = {
            ProductTypes.HARVEST_SHARES: is_harvest_shares_available(next_month),
            ProductTypes.CHICKEN_SHARES: additional_products_available
            and is_chicken_shares_available(next_month),
            ProductTypes.BESTELLCOOP: ProductTypes.BESTELLCOOP
            in context["subscriptions"]
            and additional_products_available
            and (
                not (
                    len(context["subscriptions"][ProductTypes.BESTELLCOOP]) > 0
                    and context["subscriptions"][ProductTypes.BESTELLCOOP][0].quantity
                    > 0
                )
                or context["subscriptions"][ProductTypes.BESTELLCOOP][0].cancellation_ts
                is not None
            )
            and is_bestellcoop_available(next_month),
        }

        context["deliveries"] = generate_future_deliveries(self.object)

        # FIXME: it should be easier than this to get the next payments, refactor to service somehow
        prev_payments = get_previous_payments(self.object.pk)
        today = get_today()
        for due_date, payments in prev_payments.items():
            if due_date >= today:
                context["next_payment"] = payments[0]
            else:
                break

        next_payment = list(generate_future_payments(self.object.id, 1).values())
        if len(next_payment) > 0:
            next_payment = next_payment[0][0]

        if next_payment:
            if "next_payment" not in context or (
                next_payment["due_date"] < context["next_payment"]["due_date"]
            ):
                context["next_payment"] = next_payment

        self.add_renewal_notice_context(context, next_month, today)

        subs_in_trial = get_subscriptions_in_trial_period(self.object.id)
        context["subscriptions_in_trial"] = []
        if subs_in_trial.exists():
            context["show_trial_period_notice"] = True
            context["subscriptions_in_trial"].extend(subs_in_trial)
            context["next_trial_end_date"] = min(
                subs_in_trial, key=lambda x: x.start_date
            ).start_date + relativedelta(day=1, months=1, days=-1)
        if (
            self.object.coop_entry_date is not None
            and self.object.coop_entry_date > today
            and self.object.coopsharetransaction_set.aggregate(
                quantity=Sum(F("quantity"))
            )["quantity"]
            > 0
        ):
            context["show_trial_period_notice"] = True
            context["subscriptions_in_trial"].append(
                "Beitrittserklärung zur Genossenschaft",
            )
            context["next_trial_end_date"] = (
                share_ownerships[0].valid_at + relativedelta(days=-1)
                if "next_trial_end_date" not in context
                else context["next_trial_end_date"]
            )

        email_change_requests = EmailChangeRequest.objects.filter(
            user_id=self.object.id
        )
        if email_change_requests.exists():
            context["email_change_request"] = {
                "new_email": email_change_requests[0].new_email
            }

        return context

    def add_renewal_notice_context(self, context, next_month, today):
        """
        Renewal notice:
        - show_renewal_warning = less than 3 months before next period starts
        - add_shares_disallowed = less than 1 month
        - renewal_status = "unknown", "renewed", "cancelled"
        """
        if not get_active_subscriptions().filter(member_id=self.object.id).exists():
            return

        next_growing_period = get_next_growing_period(today)
        if (
            next_growing_period
            and (today + relativedelta(months=3)) > next_growing_period.start_date
        ):
            context["next_period"] = next_growing_period
            context["add_shares_disallowed"] = (
                next_month >= next_growing_period.start_date
            )  # 1 month before

            harvest_share_subs = context["subscriptions"][ProductTypes.HARVEST_SHARES]

            if len(harvest_share_subs) < 1:
                context["show_renewal_warning"] = False
                return  # no harvest share subs, nothing to renew. Member can add subscriptions via the "+" button
            else:
                context["show_renewal_warning"] = True

            context["contract_end_date"] = contract_end_date = (
                format_date(harvest_share_subs[0].end_date)
                if type(harvest_share_subs[0]) is Subscription
                else None
            )
            cancelled = any(
                map(
                    lambda x: (None if type(x) is dict else x.cancellation_ts)
                    is not None,
                    harvest_share_subs,
                )
            )
            future_subs = get_future_subscriptions(
                next_growing_period.start_date
            ).filter(member_id=self.object.id)
            has_future_subs = future_subs.exists()
            if cancelled and not has_future_subs:
                context[
                    "renewal_status"
                ] = "cancelled"  # --> show cancellation confirmation
            elif has_future_subs:
                context["renewal_status"] = "renewed"  # --> show renewal confirmation
                if not future_subs.filter(
                    cancellation_ts__isnull=True
                ).exists():  # --> renewed but cancelled
                    context["show_renewal_warning"] = False
            else:
                if context["available_product_types"][ProductTypes.HARVEST_SHARES]:
                    context["renewal_status"] = "unknown"  # --> show renewal notice
                elif WaitingListEntry.objects.filter(
                    email=self.object.email,
                    type=WaitingListEntry.WaitingListType.HARVEST_SHARES,
                ).exists():
                    context[
                        "renewal_status"
                    ] = "waitlist"  # --> show waitlist confirmation
                else:
                    context["renewal_status"] = "no_capacity"  # --> show waitlist

            context["renewal_alert"] = {
                "unknown": {
                    "header": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_UNKOWN_HEADER,
                        contract_end_date,
                        next_growing_period,
                    ),
                    "content": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_UNKOWN_CONTENT,
                        contract_end_date,
                        next_growing_period,
                    ),
                },
                "cancelled": {
                    "header": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_CANCELLED_HEADER,
                        contract_end_date,
                        next_growing_period,
                    ),
                    "content": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_CANCELLED_CONTENT,
                        contract_end_date,
                        next_growing_period,
                    ),
                },
                "renewed": {
                    "header": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_RENEWED_HEADER,
                        contract_end_date,
                        next_growing_period,
                    ),
                    "content": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_RENEWED_CONTENT,
                        contract_end_date,
                        next_growing_period,
                        contract_list=f"{'<br/>'.join(map(lambda x: '- ' + str(x), future_subs))}<br/>",
                    ),
                },
                "no_capacity": {
                    "header": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_WAITLIST_HEADER,
                        contract_end_date,
                        next_growing_period,
                    ),
                    "content": self.format_param(
                        Parameter.MEMBER_RENEWAL_ALERT_WAITLIST_CONTENT,
                        contract_end_date,
                        next_growing_period,
                    ),
                },
            }

    def format_param(
        self,
        key: str,
        contract_end_date: str,
        next_growing_period: GrowingPeriod,
        **kwargs,
    ):
        return get_parameter_value(key).format(
            member=self.object,
            contract_end_date=contract_end_date,
            next_period_start_date=format_date(next_growing_period.start_date),
            next_period_end_date=format_date(next_growing_period.end_date),
            **kwargs,
        )
