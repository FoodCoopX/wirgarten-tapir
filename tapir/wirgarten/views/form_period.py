from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.forms.product_cfg.period_product_cfg_forms import (
    GrowingPeriodForm,
)
from tapir.wirgarten.models import (
    GrowingPeriod,
)
from tapir.wirgarten.service.products import create_growing_period, copy_growing_period
from tapir.wirgarten.views.modal import get_form_modal

PAGE_ROOT = "wirgarten:product"
KW_PERIOD_ID = "periodId"


@require_http_methods(["GET", "POST"])
def get_period_add_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=GrowingPeriodForm,
        handler=lambda form: create_growing_period(
            start_date=form.cleaned_data["start_date"],
            end_date=form.cleaned_data["end_date"],
        ),
        redirect_url_resolver=lambda data: f"{reverse_lazy(PAGE_ROOT)}?{KW_PERIOD_ID}={data.id}",
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_period_copy_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=GrowingPeriodForm,
        handler=lambda form: copy_growing_period(
            growing_period_id=form.cleaned_data["id"],
            start_date=form.cleaned_data["start_date"],
            end_date=form.cleaned_data["end_date"],
        ),
        redirect_url_resolver=lambda data: f"{reverse_lazy(PAGE_ROOT)}?{KW_PERIOD_ID}={data.id}",
        **kwargs,
    )


@require_http_methods(["GET"])
def delete_period(request, **kwargs):
    try:
        GrowingPeriod.objects.get(id=kwargs[KW_PERIOD_ID]).delete()
        return HttpResponseRedirect(reverse_lazy(PAGE_ROOT))
    except GrowingPeriod.DoesNotExist:
        return HttpResponse(status=404)
