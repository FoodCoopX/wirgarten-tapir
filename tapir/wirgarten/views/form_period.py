from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt

from tapir.wirgarten.forms.product_cfg.period_product_cfg_forms import (
    GrowingPeriodForm,
)
from tapir.wirgarten.models import (
    GrowingPeriod,
)
from tapir.wirgarten.service.products import create_growing_period, copy_growing_period

PAGE_ROOT = "wirgarten:product"
KW_PERIOD_ID = "periodId"


@require_http_methods(["GET", "POST"])
def get_period_copy_form(request, **kwargs):
    # if this is a POST request we need to process the form data

    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = GrowingPeriodForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            copy_growing_period(
                growing_period_id=form.cleaned_data["id"],
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data["end_date"],
            )
            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = GrowingPeriodForm(**kwargs)

    return render(request, "wirgarten/product_cfg/modal_form.html", {"form": form})


@require_http_methods(["GET", "POST"])
def get_period_add_form(request, **kwargs):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = GrowingPeriodForm(request.POST, **kwargs)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            create_growing_period(
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data["end_date"],
            )
            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = GrowingPeriodForm(**kwargs)

    return render(request, "wirgarten/product_cfg/modal_form.html", {"form": form})


@require_http_methods(["GET"])
def delete_period(request, **kwargs):
    try:
        GrowingPeriod.objects.get(id=kwargs[KW_PERIOD_ID]).delete()
        return HttpResponseRedirect(
            reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
        )
    except GrowingPeriod.DoesNotExist:
        return HttpResponse(status=404)
