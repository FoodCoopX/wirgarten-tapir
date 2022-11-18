import itertools
import json

from django.views import generic

from tapir.wirgarten.models import (
    ProductType,
    Product,
    ProductCapacity,
    GrowingPeriod,
    TaxRate,
)


class ProductCfgView(generic.TemplateView):
    template_name = "wirgarten/product/period_product_cfg_view.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # growing periods
        context["growing_periods"] = list(
            map(
                lambda g: {
                    "id": g.id,
                    "start_date": g.start_date,
                    "end_date": g.end_date,
                },
                GrowingPeriod.objects.all(),
            )
        )

        # product types
        context["product_types"] = ProductType.objects.all()

        # all products
        context["products"] = Product.objects.all().order_by("type")

        # growing_periods->product_types
        capacities = ProductCapacity.objects.all().order_by("period")

        context["pe_pt_map"] = json.dumps(
            {
                k: list(map(lambda p: p.product_type.id, v))
                for k, v in itertools.groupby(
                    capacities, lambda capacity: capacity.period.id
                )
            }
        )

        # product_types->products mapping
        # Done: fix problem with unordered product list
        # info: Problem is fixed through order_by; but itertools shouldn't
        # produce a wrong result, if the object aren't presorted
        context["pt_p_map"] = json.dumps(
            {
                k: list(map(lambda p: p.id, v))
                for k, v in itertools.groupby(
                    context["products"], lambda prod: prod.type.id
                )
            }
        )

        context["tax_rates"] = {
            k: round(float(list(v)[0].tax_rate) * 100.0, 1)
            for k, v in itertools.groupby(
                TaxRate.objects.filter(
                    valid_to=None, product_type__in=context["product_types"]
                ),
                lambda t: t.product_type.id,
            )
        }

        context["capacity"] = {
            k: float(list(v)[0].capacity)
            for k, v in itertools.groupby(
                ProductCapacity.objects.filter(
                    product_type__in=context["product_types"]
                ),
                lambda c: c.product_type.id,
            )
        }

        return context
