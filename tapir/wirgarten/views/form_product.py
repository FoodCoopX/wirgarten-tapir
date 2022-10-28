from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.shortcuts import render

from tapir.wirgarten.forms.product_cfg.period_product_cfg_forms import ProductForm
from tapir.wirgarten.models import Product


PAGE_ROOT = "wirgarten:product"
KW_PROD_TYPE_ID = "prodTypeId"
KW_PROD_ID = "prodId"


def save_product(form: ProductForm):
    try:
        param = Product.objects.get(id=form["id"])
        param.name = form["name"]
        param.price = form["price"]
        print("\t[update] Product ", form["id"])
        param.save()
    except ObjectDoesNotExist:
        print("\t[update] Product failed. object does not exist - ", id)


def create_product(form: ProductForm):
    print("\t[create] Product ")
    Product.objects.create(
        name=form["name"], price=form["price"], type_id=form["type_id"]
    )


@require_http_methods(["GET", "POST"])
def get_product_edit_form(request, **kwargs):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = ProductForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            save_product(form.cleaned_data)
            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ProductForm(**kwargs)

    return render(
        request, "wirgarten/product_cfg/period_product_cfg.html", {"form": form}
    )


@require_http_methods(["GET", "POST"])
def get_product_add_form(request, **kwargs):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = ProductForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            form.cleaned_data["type_id"] = kwargs[KW_PROD_TYPE_ID]
            create_product(form.cleaned_data)
            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ProductForm(**kwargs)

    return render(
        request, "wirgarten/product_cfg/period_product_cfg.html", {"form": form}
    )


@require_http_methods(["GET"])
def delete_product(request, **kwargs):
    try:
        Product.objects.get(id=kwargs[KW_PROD_ID]).delete()
        return HttpResponseRedirect(
            reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
        )
    except Product.DoesNotExist:
        return HttpResponse(status=404)
