from django.views.decorators.http import require_http_methods
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render

from tapir.wirgarten.forms.product_cfg.period_product_cfg_forms import (
    ProductTypeForm,
    GrowingPeriodForm,
)
from tapir.wirgarten.models import (
    ProductCapacity,
    GrowingPeriod,
)


PAGE_ROOT = "wirgarten:product"
KW_PERIOD_ID = "periodId"


def create_period(form: ProductTypeForm):
    # period
    print("\t[create] GrowingPeriod\n")
    gp = GrowingPeriod.objects.create(
        start_date=form["start_date"],
        end_date=form["end_date"],
    )
    return gp


def copy_create_period(form: ProductTypeForm):
    gp = create_period(form)
    capacities = ProductCapacity.objects.filter(period_id=form["id"])
    for capacity in capacities:
        cp = ProductCapacity.objects.create(
            period_id=gp.id,
            product_type=capacity.product_type,
            capacity=capacity.capacity,
        )
        print("\n\t[create] Capacity\n", cp.id)


@require_http_methods(["GET", "POST"])
def get_period_copy_form(request, **kwargs):
    # if this is a POST request we need to process the form data

    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = GrowingPeriodForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            copy_create_period(form.cleaned_data)
            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = GrowingPeriodForm(**kwargs)

    return render(
        request, "wirgarten/product_cfg/period_product_cfg.html", {"form": form}
    )


@require_http_methods(["GET", "POST"])
def get_period_add_form(request, **kwargs):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = GrowingPeriodForm(request.POST, **kwargs)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            create_period(form.cleaned_data)
            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = GrowingPeriodForm(**kwargs)

    return render(
        request, "wirgarten/product_cfg/period_product_cfg.html", {"form": form}
    )


@require_http_methods(["GET"])
def delete_period(request, **kwargs):
    try:
        GrowingPeriod.objects.get(id=kwargs[KW_PERIOD_ID]).delete()
        return HttpResponseRedirect(
            reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
        )
    except GrowingPeriod.DoesNotExist:
        return HttpResponse(status=404)
