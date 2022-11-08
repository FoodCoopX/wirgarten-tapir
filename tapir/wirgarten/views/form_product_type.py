from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist
from datetime import date
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render

from tapir.wirgarten.forms.product_cfg.period_product_cfg_forms import ProductTypeForm
from tapir.wirgarten.models import ProductType, ProductCapacity, TaxRate, Product  #


PAGE_ROOT = "wirgarten:product"
KW_PROD_TYPE_ID = "prodTypeId"
KW_PERIOD_ID = "periodId"


def save_product_type(form: ProductTypeForm):
    try:
        # product
        pt = ProductType.objects.get(id=form["id"])
        pt.name = form["name"]
        pt.delivery_cycle = form["delivery_cycle"]
        print("\t[update] ProductType ", form["id"])
        pt.save()
    except ObjectDoesNotExist:
        print("\t[update] ProductType failed. object does not exist - ", id)

    try:
        # capacity
        cp = ProductCapacity.objects.get(
            period__id=form["periodId"], product_type__id=form["id"]
        )
        cp.capacity = form["capacity"]
        cp.save()
    except ObjectDoesNotExist:
        print(
            "\t[update] ProductType failed. related ProductCapacity does not exist - ",
            id,
        )

    # tax rate
    try:
        tr = TaxRate.objects.get(product_type__id=form["id"], valid_to=None)
        if tr.tax_rate != form["tax_rate"]:
            tr.valid_to = date.today()
            tr.save()

            TaxRate.objects.create(
                product_type_id=form["id"],
                tax_rate=form["tax_rate"],
                valid_from=date.today(),
                valid_to=None,
            )
    except ObjectDoesNotExist:
        print("\t[update] Warning: prior TaxRate does not exist - ", id)
        TaxRate.objects.create(
            product_type_id=form["id"],
            tax_rate=form["tax_rate"],
            valid_from=date.today(),
            valid_to=None,
        )


def create_product_type(form: ProductTypeForm, period_id):
    # product type
    print("\t[create] ProductType ")
    pt = ProductType.objects.create(
        name=form["name"],
        delivery_cycle=form["delivery_cycle"],
    )
    # tax rate
    TaxRate.objects.create(
        product_type_id=pt.id,
        tax_rate=form["tax_rate"],
        valid_from=date.today(),
        valid_to=None,
    )
    # capacity
    ProductCapacity.objects.create(
        period_id=period_id,
        product_type=pt,
        capacity=form["capacity"],
    )


@require_http_methods(["GET", "POST"])
def get_product_type_edit_form(request, **kwargs):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = ProductTypeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            save_product_type(form.cleaned_data)
            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ProductTypeForm(**kwargs)

    return render(
        request, "wirgarten/product_cfg/period_product_cfg.html", {"form": form}
    )


@require_http_methods(["GET", "POST"])
def get_product_type_add_form(request, **kwargs):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = ProductTypeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            form.cleaned_data["period_id"] = kwargs[KW_PERIOD_ID]
            create_product_type(form.cleaned_data, kwargs[KW_PERIOD_ID])
            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
            )

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ProductTypeForm(**kwargs)

    return render(
        request, "wirgarten/product_cfg/period_product_cfg.html", {"form": form}
    )


@require_http_methods(["GET"])
def delete_product_type(request, **kwargs):
    try:
        ProductCapacity.objects.get(
            period__id=kwargs[KW_PERIOD_ID], product_type__id=kwargs[KW_PROD_TYPE_ID]
        ).delete()

        try:
            if ProductCapacity.objects.filter(
                product_type__id=kwargs[KW_PROD_TYPE_ID]
            ).exists():
                print(
                    "Delete ProductType: Product type is still referenced, just deleting product capacity."
                )
        except ProductCapacity.DoesNotExist:
            print(
                "Delete ProductType: Product type is not referenced anymore, trying to delete product type, related tax rates and products."
            )
            try:
                Product.objects.filter(type__id=kwargs[KW_PROD_TYPE_ID]).delete()
                TaxRate.objects.filter(
                    product_type__id=kwargs[KW_PROD_TYPE_ID]
                ).delete()
                ProductType.objects.get(id=kwargs[KW_PROD_TYPE_ID]).delete()
                print("Delete ProductType: [success].")
            # except Product.DoesNotExist:
            #     print('Delete ProductType: [warning] no related products do exist.')
            # except TaxRate.DoesNotExist:
            #     print('Delete ProductType: [warning] no related Tax rates do exist.')
            except ProductType.DoesNotExist:
                print("Delete ProductType: [fail] Product type does not exist.")

        return HttpResponseRedirect(
            reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
        )
    except ProductType.DoesNotExist:
        return HttpResponse(status=404)
