from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Deliveries, Member, Subscription
from tapir.wirgarten.service.delivery import generate_future_deliveries
from tapir.wirgarten.views.mixin import PermissionOrSelfRequiredMixin
from django.views import generic


def get_previous_deliveries(member: Member):
    return list(
        map(
            lambda x: {
                "pickup_location": x.pickup_location,
                "delivery_date": x.delivery_date,
                "subs": Subscription.objects.filter(
                    member=x.member,
                    start_date__lte=x.due_date,
                    end_date__gt=x.due_date,
                ),
            },
            Deliveries.objects.filter(member=member),
        )
    )


class MemberDeliveriesView(
    PermissionOrSelfRequiredMixin, generic.TemplateView, generic.base.ContextMixin
):
    template_name = "wirgarten/member/member_deliveries.html"
    permission_required = Permission.Accounts.VIEW

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_id = kwargs["pk"]

        member = Member.objects.get(pk=member_id)

        context["member"] = member
        context["deliveries"] = get_previous_deliveries(
            member
        ) + generate_future_deliveries(member)

        return context
