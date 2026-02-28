from django.views.generic import TemplateView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class IngredientsLabelsBreadsView(TemplateView):
    template_name = "bakery/ingredients_labels_breads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class ReportsView(TemplateView):
    template_name = "bakery/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class WeeklyPlanBreadsView(TemplateView):
    template_name = "bakery/weekly_plan_breads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class ChooseBreadsView(TemplateView):
    template_name = "bakery/choose_breads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["member_id"] = self.request.GET.get("member_id", self.request.user.pk)
        context["bakery_enabled"] = get_parameter_value(ParameterKeys.BAKERY_ENABLED)
        context["choose_station_per_bread"] = get_parameter_value(
            ParameterKeys.BAKERY_PICKUP_LOCATIONS_CAN_BE_CHOSEN_PER_SHARE
        )
        context["members_can_choose_bread_sorts"] = get_parameter_value(
            ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS
        )

        return context
