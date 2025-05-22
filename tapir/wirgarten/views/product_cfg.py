import itertools
import json
import re

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

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
from tapir.wirgarten.utils import get_today
from tapir.wirgarten.views.modal import get_form_modal

PAGE_ROOT = "wirgarten:product"
KW_CAPACITY_ID = "capacityId"
KW_PERIOD_ID = "periodId"
KW_PROD_ID = "prodId"


class ProductCfgView(PermissionRequiredMixin, generic.TemplateView):
    template_name = "wirgarten/product/period_product_cfg_view.html"
    permission_required = Permission.Products.VIEW

    @staticmethod
    def get_growing_period_status(period) -> str:
        today = get_today()
        if period.end_date < today:
            return "old"
        elif period.start_date <= today <= period.end_date:
            return "active"
        elif period.start_date > today:
            return "upcoming"
        else:
            return ""

    @staticmethod
    def get_current_product_price(product_prices: list[ProductPrice]) -> ProductPrice:
        if len(product_prices) == 1:
            return product_prices[0]

        valid_product_prices = [
            product_price
            for product_price in product_prices
            if product_price.valid_from <= get_today()
        ]
        return sorted(
            valid_product_prices, key=lambda product_price: product_price.valid_from
        )[-1]

    @classmethod
    def build_product_object_for_context(cls, product, product_prices):

        return {
            "id": product.id,
            "name": product.name,
            "type_id": product.type.id,
            "prices": product_prices,
            "deleted": product.deleted,
            "base": product.base,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # growing periods
        context["growing_periods"] = list(
            map(
                lambda growing_period: {
                    "id": growing_period.id,
                    "status": self.get_growing_period_status(growing_period),
                    "start_date": growing_period.start_date,
                    "end_date": growing_period.end_date,
                },
                GrowingPeriod.objects.all().order_by("-start_date"),
            )
        )

        product_prices_by_product_id = itertools.groupby(
            ProductPrice.objects.all().order_by("product__id", "-valid_from"),
            lambda product_price: product_price.product.id,
        )
        product_prices_by_product_id = {
            product_id: list(product_prices)[:2]
            for product_id, product_prices in product_prices_by_product_id
        }

        # all products
        products = [
            self.build_product_object_for_context(
                product, product_prices_by_product_id.get(product.id, [])
            )
            for product in Product.objects.all().order_by("type")
        ]
        context["products"] = sorted(
            products, key=lambda product: product["prices"][0].price
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
                                lambda ppi: ppi.valid_from < capacity.period.end_date,
                                p["prices"],
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
                    g["id"]: {"delete": g["status"] == "upcoming"}
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
        form_class=ProductTypeForm,
        handler=lambda form: update_product_type_capacity(
            id_=kwargs[KW_CAPACITY_ID],
            name=form.cleaned_data["name"],
            contract_link=form.cleaned_data["contract_link"],
            icon_link=form.cleaned_data["icon_link"],
            single_subscription_only=form.cleaned_data["single_subscription_only"],
            delivery_cycle=form.cleaned_data["delivery_cycle"],
            default_tax_rate=form.cleaned_data["tax_rate"],
            capacity=form.cleaned_data["capacity"],
            tax_rate_change_date=form.cleaned_data["tax_rate_change_date"],
            is_affected_by_jokers=form.cleaned_data["is_affected_by_jokers"],
            notice_period_duration=form.cleaned_data["notice_period"],
            must_be_subscribed_to=form.cleaned_data["must_be_subscribed_to"],
            is_association_membership=form.cleaned_data.get(
                "is_association_membership", False
            ),
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
            contract_link=form.cleaned_data["contract_link"],
            icon_link=form.cleaned_data["icon_link"],
            single_subscription_only=form.cleaned_data["single_subscription_only"],
            delivery_cycle=form.cleaned_data["delivery_cycle"],
            default_tax_rate=form.cleaned_data["tax_rate"],
            capacity=form.cleaned_data["capacity"],
            period_id=kwargs[KW_PERIOD_ID],
            notice_period_duration=form.cleaned_data["notice_period"],
            is_affected_by_jokers=form.cleaned_data.get("is_affected_by_jokers", False),
            must_be_subscribed_to=form.cleaned_data["must_be_subscribed_to"],
            is_association_membership=form.cleaned_data.get(
                "is_association_membership", False
            ),
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
        form_class=ProductTypeForm,
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
        form_class=ProductForm,
        handler=lambda form: update_product(
            id_=form.cleaned_data["id"],
            name=form.cleaned_data["name"],
            base=form.cleaned_data["base"],
            price=form.cleaned_data["price"],
            size=form.cleaned_data["size"],
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
        form_class=ProductForm,
        handler=lambda form: create_product(
            name=form.cleaned_data["name"],
            price=form.cleaned_data["price"],
            capacity_id=kwargs[KW_CAPACITY_ID],
            base=form.cleaned_data["base"],
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
        form_class=GrowingPeriodForm,
        handler=lambda form: create_growing_period(
            start_date=form.cleaned_data["start_date"],
            end_date=form.cleaned_data["end_date"],
            max_jokers_per_member=form.cleaned_data.get("max_jokers_per_member", 0),
            joker_restrictions="disabled",
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
        form_class=GrowingPeriodForm,
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
