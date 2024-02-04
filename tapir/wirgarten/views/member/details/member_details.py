from dateutil.relativedelta import relativedelta
from django.db.models import F, Sum
from django.utils.translation import gettext_lazy as _
from django.views import generic

from tapir.accounts.models import EmailChangeRequest
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import Permission, ProductTypes
from tapir.wirgarten.models import (
    CoopShareTransaction,
    GrowingPeriod,
    Member,
    ProductType,
    Subscription,
    WaitingListEntry,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import generate_future_deliveries
from tapir.wirgarten.service.member import (
    get_next_contract_start_date,
    get_subscriptions_in_trial_period,
)
from tapir.wirgarten.service.payment import (
    get_active_subscriptions_grouped_by_product_type,
    get_next_payment_date,
)
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_active_subscriptions,
    get_available_product_types,
    get_future_subscriptions,
    get_next_growing_period,
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

        product_types = get_active_product_types(reference_date=next_month)
        types_to_remove = []
        product_type_names = list(map(lambda x: x.name, product_types))
        for key in context["subscriptions"].keys():
            if key not in product_type_names:
                types_to_remove.append(key)
        for key in types_to_remove:
            del context["subscriptions"][key]

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

        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        context["available_product_types"] = {
            p.name: p.id == base_product_type_id
            or (
                additional_products_available
                and (
                    p.single_subscription_only
                    and not Subscription.objects.filter(
                        member_id=self.object.id, product__type_id=p.id
                    ).exists()
                )
                or not p.single_subscription_only
            )
            for p in get_available_product_types(reference_date=next_month)
        }
        context["deliveries"] = generate_future_deliveries(self.object)

        # FIXME: it should be easier than this to get the next payments, refactor to service somehow
        next_due_date = get_next_payment_date()

        persisted_payments = get_previous_payments(self.object.pk)
        next_payments = persisted_payments.get(next_due_date, [])

        projected = generate_future_payments(self.object.id, 2)
        if len(projected) > 0:
            projected = projected.get(next_due_date, [])
            for p in projected:
                if p["type"] not in [n["type"] for n in next_payments]:
                    next_payments.append(p)

        context["next_payment"] = (
            {
                "due_date": next_due_date,
                "amount": sum([p["amount"] for p in next_payments]),
                "mandate_ref": next_payments[0]["mandate_ref"],
            }
            if next_payments
            else None
        )

        self.add_renewal_notice_context(context, next_month, today)

        subs_in_trial = get_subscriptions_in_trial_period(self.object.id)
        context["subscriptions_in_trial"] = []
        if subs_in_trial:
            context["show_trial_period_notice"] = True
            context["subscriptions_in_trial"].extend(subs_in_trial)
            context["next_trial_end_date"] = min(
                subs_in_trial, key=lambda x: x.trial_end_date
            ).trial_end_date

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
        if not (
            next_growing_period
            and (today + relativedelta(months=3)) > next_growing_period.start_date
        ):
            return

        context["next_period"] = next_growing_period
        context["add_shares_disallowed"] = (
            next_month >= next_growing_period.start_date
        )  # 1 month before

        base_product_type = ProductType.objects.get(
            id=get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        )
        harvest_share_subs = context["subscriptions"][base_product_type.name]
        context["base_product_type_name"] = base_product_type.name

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
                lambda x: (None if type(x) is dict else x.cancellation_ts) is not None,
                harvest_share_subs,
            )
        )
        future_subs = get_future_subscriptions(next_growing_period.start_date).filter(
            member_id=self.object.id
        )
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
            if context["available_product_types"][base_product_type.name]:
                context["renewal_status"] = "unknown"  # --> show renewal notice
            elif WaitingListEntry.objects.filter(
                email=self.object.email,
                type=WaitingListEntry.WaitingListType.HARVEST_SHARES,
            ).exists():
                context["renewal_status"] = "waitlist"  # --> show waitlist confirmation
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
