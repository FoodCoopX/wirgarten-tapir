from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.http import require_GET

from tapir.configuration.forms import ParameterForm
from tapir.configuration.models import TapirParameter


@require_GET
@permission_required("coop.manage")
def member_number_preview(request):
    prefix = request.GET.get("prefix", "")
    try:
        length = int(request.GET.get("length", "0"))
    except (ValueError, TypeError):
        length = 0
    example_numbers = [17, 1234, 123456]
    previews = [f"{prefix}{n:0{max(length, 0)}}" for n in example_numbers]
    return JsonResponse({"previews": previews})


class ParameterView(PermissionRequiredMixin, generic.FormView):
    template_name = "configuration/parameter_view.html"
    permission_required = "coop.manage"
    form_class = ParameterForm

    def get_context_data(self, **kwargs):
        from tapir.wirgarten.parameter_keys import ParameterKeys

        context = super().get_context_data(**kwargs)
        context["member_number_prefix_key"] = ParameterKeys.MEMBER_NUMBER_PREFIX
        context["member_number_length_key"] = (
            ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH
        )
        return context

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
