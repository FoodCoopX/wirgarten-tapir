from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class IngredientsLabelsBreadsView(LoginRequiredMixin, TemplateView):
    template_name = "bakery/ingredients_labels_breads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = "bakery/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class WeeklyPlanBreadsView(LoginRequiredMixin, TemplateView):
    template_name = "bakery/weekly_plan_breads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class ChooseBreadsView(TemplateView):
    template_name = "bakery/pages/choose_breads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["member_id"] = self.request.GET.get("member_id", self.request.user.pk)
        return context
