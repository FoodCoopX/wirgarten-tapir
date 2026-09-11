from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404
from django.views.generic import TemplateView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import check_permission_or_self


class BakeryAdminTemplateView(
    LoginRequiredMixin, PermissionRequiredMixin, TemplateView
):
    """Base for the bakery pages that show data across the whole co-op."""

    permission_required = Permission.Coop.MANAGE

    def get(self, request, *args, **kwargs):
        # In get(), not dispatch(): the login and permission checks run first,
        # so an unauthorised caller gets 401/403 and only somebody who may see
        # the page learns that the feature is switched off.
        if not get_parameter_value(ParameterKeys.BAKERY_A_ENABLED):
            raise Http404("Die Bäckerei-Funktion ist nicht aktiviert.")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class IngredientsLabelsBreadsView(BakeryAdminTemplateView):
    template_name = "bakery/ingredients_labels_breads.html"


class ReportsView(BakeryAdminTemplateView):
    template_name = "bakery/reports.html"


class WeeklyPlanBreadsView(BakeryAdminTemplateView):
    template_name = "bakery/weekly_plan_breads.html"


class ChooseBreadsView(LoginRequiredMixin, TemplateView):
    """
    The one member-facing bakery page.

    LoginRequiredMixin without raise_exception, like every other member page:
    an anonymous caller is redirected to the login page rather than dead-ended
    on a 403.
    """

    template_name = "bakery/choose_breads.html"

    def get(self, request, *args, **kwargs):
        if not get_parameter_value(ParameterKeys.BAKERY_A_ENABLED):
            raise Http404("Die Bäckerei-Funktion ist nicht aktiviert.")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        member_id = self.request.GET.get("member_id", self.request.user.pk)
        # member_id is attacker-controlled, so it has to be checked before the
        # page hands it to the bread-delivery and preference endpoints.
        check_permission_or_self(member_id, self.request)

        context["member_id"] = member_id
        context["choose_station_per_bread"] = get_parameter_value(
            ParameterKeys.BAKERY_PICKUP_LOCATIONS_CAN_BE_CHOSEN_PER_SHARE
        )
        context["members_can_choose_bread_sorts"] = get_parameter_value(
            ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS
        )

        return context
