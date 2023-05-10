import datetime
import itertools
import json
import re

from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import permission_required
from django.views.decorators.csrf import csrf_protect

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.product_cfg.period_product_cfg_forms import (
    ProductTypeForm,
    ProductForm,
    GrowingPeriodForm,
)
from tapir.wirgarten.models import (
    ProductType,
    Product,
    ProductCapacity,
    GrowingPeriod,
    TaxRate,
    ProductPrice,
)
from tapir.wirgarten.service.products import (
    create_product_type_capacity,
    update_product_type_capacity,
    delete_product_type_capacity,
    create_product,
    delete_product,
    delete_growing_period_with_capacities,
    copy_growing_period,
    create_growing_period,
    update_product,
)
from tapir.wirgarten.views.modal import get_form_modal

PAGE_ROOT = "wirgarten:product"
KW_CAPACITY_ID = "capacityId"
KW_PERIOD_ID = "periodId"
KW_PROD_ID = "prodId"


class ProductCfgView(PermissionRequiredMixin, generic.TemplateView):
    template_name = "wirgarten/product/period_product_cfg_view.html"
    permission_required = Permission.Products.VIEW

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        def get_growing_period_status(period) -> str:
            today = datetime.date.today()
            if period.end_date < today:
                return "old"
            elif period.start_date < today and period.end_date > today:
                return "active"
            elif period.start_date > today:
                return "upcoming"
            else:
                return ""

        # growing periods
        context["growing_periods"] = list(
            map(
                lambda g: {
                    "id": g.id,
                    "status": get_growing_period_status(g),
                    "start_date": g.start_date,
                    "end_date": g.end_date,
                },
                GrowingPeriod.objects.all().order_by("-start_date"),
            )
        )

        product_prices = {
            k: list(
                map(
                    lambda price: {
                        "valid_from": price.valid_from,
                        "price": price.price,
                    },
                    list(v)[:2],
                )
            )
            for k, v in itertools.groupby(
                ProductPrice.objects.all().order_by("product__id", "-valid_from"),
                lambda pp: pp.product.id,
            )
        }

        # all products
        context["products"] = sorted(
            list(
                map(
                    lambda p: {
                        "id": p.id,
                        "name": p.name,
                        "type_id": p.type.id,
                        "price": product_prices.get(p.id, []),
                        "deleted": p.deleted,
                        "base": p.base,
                    },
                    Product.objects.all().order_by("type"),
                )
            ),
            key=lambda p: p["price"][0]["price"],
        )

        # growing_periods->product_types
        context["capacities"] = list(
            ProductCapacity.objects.all().order_by("period", "product_type__name")
        )

        context["pe_c_map"] = json.dumps(
            {
                k: list(map(lambda c: c.id, v))
                for k, v in itertools.groupby(
                    context["capacities"], lambda capacity: capacity.period.id
                )
            }
        )

        c_p_map = {
            capacity.id: list(
                map(
                    lambda x: x["id"],
                    filter(
                        lambda p: p["type_id"] == capacity.product_type.id
                        and any(
                            map(
                                lambda ppi: ppi["valid_from"]
                                < capacity.period.end_date,
                                p["price"],
                            )
                        ),
                        context["products"],
                    ),
                )
            )
            for capacity in context["capacities"]
        }
        context["c_p_map"] = json.dumps(c_p_map)

        context["tax_rates"] = {
            k: round(float(list(v)[0].tax_rate) * 100.0, 1)
            for k, v in itertools.groupby(
                TaxRate.objects.filter(
                    valid_to=None, product_type__in=ProductType.objects.all()
                ),
                lambda t: t.product_type.id,
            )
        }

        context["buttons"] = json.dumps(
            {
                "period": {
                    g["id"]: {"delete": g["status"] is "upcoming"}
                    for g in context["growing_periods"]
                },
                "capacity": {
                    c.id: {"delete": len(c_p_map[c.id]) == 0}
                    for c in context["capacities"]
                },
            }
        )

        return context


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Products.MANAGE)
@csrf_protect
def get_product_type_capacity_edit_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=ProductTypeForm,
        handler=lambda form: update_product_type_capacity(
            id_=kwargs[KW_CAPACITY_ID],
            name=form.cleaned_data["name"],
            delivery_cycle=form.cleaned_data["delivery_cycle"],
            default_tax_rate=form.cleaned_data["tax_rate"],
            capacity=form.cleaned_data["capacity"],
            tax_rate_change_date=form.cleaned_data["tax_rate_change_date"],
        ),
        redirect_url_resolver=lambda data: f"""{reverse_lazy(PAGE_ROOT)}?{request.environ["QUERY_STRING"]}""",
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Products.MANAGE)
@csrf_protect
def get_product_type_capacity_add_form(request, **kwargs):
    def handler(form):
        return create_product_type_capacity(
            name=form.cleaned_data["name"],
            delivery_cycle=form.cleaned_data["delivery_cycle"],
            default_tax_rate=form.cleaned_data["tax_rate"],
            capacity=form.cleaned_data["capacity"],
            period_id=kwargs[KW_PERIOD_ID],
            product_type_id=form.cleaned_data["product_type"],
        )

    def redirect_url(data):
        new_query_string = (
            re.sub(f"{KW_CAPACITY_ID}=([\d\w]*)&?", "", request.environ["QUERY_STRING"])
            + f"&{KW_CAPACITY_ID}={data.id}"
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
@permission_required(Permission.Products.MANAGE)
@csrf_protect
def delete_product_type(request, **kwargs):
    delete_product_type_capacity(kwargs[KW_CAPACITY_ID])

    return HttpResponseRedirect(
        reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
    )


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Products.MANAGE)
@csrf_protect
def get_product_edit_form(request, **kwargs):
    return get_form_modal(
        request=request,
        form=ProductForm,
        handler=lambda form: update_product(
            id_=form.cleaned_data["id"],
            name=form.cleaned_data["name"],
            price=form.cleaned_data["price"],
            growing_period_id=kwargs[KW_PERIOD_ID],
        ),
        redirect_url_resolver=lambda data: f"""{reverse_lazy(PAGE_ROOT)}?{request.environ["QUERY_STRING"]}""",
        **kwargs,
    )


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Products.MANAGE)
@csrf_protect
def get_product_add_form(request, **kwargs):
    def redirect_url(data):
        new_query_string = (
            re.sub(f"{KW_PROD_ID}=([\d\w]*)&?", "", request.environ["QUERY_STRING"])
            + f"&{KW_PROD_ID}={data.id}"
        )
        return f"{reverse_lazy(PAGE_ROOT)}?{new_query_string}"

    return get_form_modal(
        request=request,
        form=ProductForm,
        handler=lambda form: create_product(
            name=form.cleaned_data["name"],
            price=form.cleaned_data["price"],
            capacity_id=kwargs[KW_CAPACITY_ID],
        ),
        redirect_url_resolver=redirect_url,
        **kwargs,
    )


@require_http_methods(["GET"])
@permission_required(Permission.Products.MANAGE)
@csrf_protect
def delete_product_handler(request, **kwargs):
    delete_product(kwargs[KW_PROD_ID])

    return HttpResponseRedirect(
        reverse_lazy(PAGE_ROOT) + "?" + request.environ["QUERY_STRING"]
    )


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
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
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
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
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def delete_period(request, **kwargs):
    delete_growing_period_with_capacities(kwargs[KW_PERIOD_ID])
    return HttpResponseRedirect(reverse_lazy(PAGE_ROOT))
