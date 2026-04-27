from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views import generic

from tapir.configuration.forms import ParameterForm
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys


class ParameterView(PermissionRequiredMixin, generic.FormView):
    template_name = "configuration/parameter_view.html"
    permission_required = "coop.manage"
    form_class = ParameterForm

    def get_success_url(self, **kwargs):
        return (
            reverse_lazy("configuration:parameters")
            + "?"
            + self.request.environ["QUERY_STRING"]
            + "&success=true"
        )

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        for field in form.visible_fields():
            TapirParameter.objects.filter(pk=field.name).update(
                value=str(form.cleaned_data[field.name])
            )

        return response

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["mandate_reference_pattern_key"] = (
            ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN
        )
        return context_data
