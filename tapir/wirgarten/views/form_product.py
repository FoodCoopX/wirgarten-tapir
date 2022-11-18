import re

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.forms.product_cfg.period_product_cfg_forms import ProductForm
from tapir.wirgarten.models import Product
from tapir.wirgarten.views.modal import get_form_modal

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
    return Product.objects.create(
        name=form["name"], price=form["price"], type_id=form["type_id"]
    )


@require_http_methods(["GET", "POST"])
def get_product_edit_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=ProductForm,
        handler=lambda form: save_product(form.cleaned_data),
        redirect_url_resolver=lambda data: f"""{reverse_lazy(PAGE_ROOT)}?{request.environ["QUERY_STRING"]}""",
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
def get_product_add_form(request, **kwargs):
    def handler(form):
        form.cleaned_data["type_id"] = kwargs[KW_PROD_TYPE_ID]
        return create_product(form.cleaned_data)

    def redirect_url(data):
        new_query_string = (
            re.sub(f"{KW_PROD_ID}=([\d\w]*)&?", "", request.environ["QUERY_STRING"])
            + f"&{KW_PROD_ID}={data.id}"
        )
        return f"{reverse_lazy(PAGE_ROOT)}?{new_query_string}"

    return get_form_modal(
        request=request,
        form=ProductForm,
        handler=handler,
        redirect_url_resolver=redirect_url,
        **kwargs,
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
