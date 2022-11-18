import re
from datetime import date

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.forms.product_cfg.period_product_cfg_forms import ProductTypeForm
from tapir.wirgarten.models import ProductType, ProductCapacity, TaxRate, Product  #
from tapir.wirgarten.views.modal import get_form_modal

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

    return pt


@require_http_methods(["GET", "POST"])
def get_product_type_edit_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=ProductTypeForm,
        handler=lambda form: save_product_type(form.cleaned_data),
        redirect_url_resolver=lambda data: f"""{reverse_lazy(PAGE_ROOT)}?{request.environ["QUERY_STRING"]}""",
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_product_type_add_form(request, **kwargs):
    def handler(form):
        form.cleaned_data["period_id"] = kwargs[KW_PERIOD_ID]
        return create_product_type(form.cleaned_data, kwargs[KW_PERIOD_ID])

    def redirect_url(data):
        new_query_string = (
            re.sub(
                f"{KW_PROD_TYPE_ID}=([\d\w]*)&?", "", request.environ["QUERY_STRING"]
            )
            + f"&{KW_PROD_TYPE_ID}={data.id}"
        )
        return f"{reverse_lazy(PAGE_ROOT)}?{new_query_string}"

    return get_form_modal(
        request=request,
        form=ProductTypeForm,
        handler=handler,
        redirect_url_resolver=redirect_url,
        **kwargs,
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
