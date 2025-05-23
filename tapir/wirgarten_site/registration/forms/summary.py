from dateutil.relativedelta import relativedelta
from django import forms
from django.utils.translation import gettext_lazy as _

from tapir import settings
from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import DeliveryCycleDict
from tapir.wirgarten.forms.subscription import BASE_PRODUCT_FIELD_PREFIX
from tapir.wirgarten.models import Product, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_next_delivery_date_for_product_type
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.utils import legal_status_is_cooperative


class SummaryForm(forms.Form):
    def is_valid(self):
        return True

    def __init__(self, *args, **kwargs):
        self.cache = kwargs.pop("cache", {})
        super().__init__(*args, **kwargs)
        initial = kwargs["initial"]

        start_date = initial["general"]["start_date"]
        end_date = initial["general"]["end_date"]

        # prepare data for the summary template
        self.harvest_shares = dict()
        self.harvest_shares_info = dict()

        base_product_type = BaseProductTypeService.get_base_product_type(
            cache=self.cache
        )

        harvest_share_products = {
            f"{BASE_PRODUCT_FIELD_PREFIX}{p.name}": p
            for p in list(Product.objects.filter(deleted=False, type=base_product_type))
        }

        for key, val in initial["base_product"].items():
            if key.startswith("base_product"):
                self.harvest_shares[key] = {
                    "amount": val,
                    "price": "{:.2f}".format(
                        get_product_price(harvest_share_products[key], start_date).price
                    ),
                    "name": _(
                        harvest_share_products[key].name + "-" + base_product_type.name
                    ),
                }
            else:
                self.harvest_shares_info[key] = val

        harvest_shares_total = sum(
            map(
                lambda i: (i.get("amount", 0) or 0) * float((i.get("price", 0) or 0)),
                self.harvest_shares.values(),
            )
        )

        solidarity_price_value = self.harvest_shares_info.get(
            "solidarity_price_harvest_shares", 0
        )

        if solidarity_price_value != "custom":
            solidarity_price = float(harvest_shares_total) * float(
                self.harvest_shares_info["solidarity_price_harvest_shares"]
            )
            self.harvest_shares_info["custom_soliprice"] = False
        else:
            solidarity_price = float(
                self.harvest_shares_info["solidarity_price_absolute_harvest_shares"]
            )
            self.harvest_shares_info["custom_soliprice"] = True

        self.total_monthly = float(harvest_shares_total) + solidarity_price

        self.harvest_shares_info["start_date"] = start_date
        self.harvest_shares_info["end_date"] = end_date

        self.harvest_shares_info["delivery_interval"] = DeliveryCycleDict[
            base_product_type.delivery_cycle
        ]

        self.harvest_shares_info["has_shares"] = harvest_shares_total > 0
        self.harvest_shares_info["total_without_solidarity"] = "{:.2f}".format(
            harvest_shares_total
        )
        self.harvest_shares_info["total"] = "{:.2f}".format(self.total_monthly)
        self.harvest_shares_info["solidarity_price_diff"] = "{:+.2f}".format(
            solidarity_price
        ).replace("+", "+ ")

        delivery_date_offset = 0
        if "pickup_location" in initial:
            pl = initial["pickup_location"]["pickup_location"]
            self.pickup_location = "{val.name}<br/><small>{val.street}<br/>{val.postcode} {val.city}<br/><br/>{val.opening_times_html}</small>".format(
                val=pl
            )  # get pickup location text
            delivery_date_offset = pl.delivery_date_offset

        self.harvest_shares_info["first_delivery_date"] = (
            get_next_delivery_date_for_product_type(
                base_product_type, start_date, cache=self.cache
            )
            + relativedelta(days=delivery_date_offset)
        )

        coop_share_price = settings.COOP_SHARE_PRICE
        coop_shares_amount = int(
            initial["coop_shares"]["cooperative_shares"] / coop_share_price
        )
        self.total_onetime = coop_shares_amount * coop_share_price

        self.coop_shares = {
            "amount": coop_shares_amount,
            "price": "{:.2f}".format(coop_share_price),
            "total": "{:.2f}".format(coop_share_price * coop_shares_amount),
            "statute_link": get_parameter_value(
                ParameterKeys.COOP_STATUTE_LINK, cache=self.cache
            ),
        }

        self.additional_product_infos = []
        for product_type in ProductType.objects.exclude(id=base_product_type.id):
            self.additional_product_infos.append(
                self.build_additional_product_type_infos(
                    product_type=product_type,
                    start_date=start_date,
                    end_date=end_date,
                    initial=initial,
                    delivery_date_offset=delivery_date_offset,
                )
            )

        self.total_monthly = "{:.2f}".format(self.total_monthly)
        self.total_onetime = "{:.2f}".format(self.total_onetime)

        self.show_cooperative_content = legal_status_is_cooperative(cache=self.cache)

    def build_additional_product_type_infos(
        self,
        product_type: ProductType,
        start_date,
        end_date,
        delivery_date_offset,
        initial,
    ):
        infos = dict(
            {
                "name": product_type.name,
                "has_shares": False,
                "start_date": start_date,
                "end_date": end_date,
                "delivery_interval": DeliveryCycleDict[product_type.delivery_cycle],
                "first_delivery_date": get_next_delivery_date_for_product_type(
                    product_type, start_date, cache=self.cache
                )
                + relativedelta(days=delivery_date_offset),
            }
        )

        key_in_initial = f"additional_product_{product_type.name}"
        if key_in_initial not in initial["additional_shares"]:
            return infos

        products = TapirCache.get_products_with_product_type(
            cache=self.cache, product_type_id=product_type.id
        )
        products_map = {
            f"{product.type_id}_{product.name}": product for product in products
        }

        shares = dict()
        for product_field_name, val in initial["additional_shares"][
            key_in_initial
        ].items():
            val = int(val)
            if product_field_name in products_map:
                shares[product_field_name] = {
                    "amount": val,
                    "price": "{:.2f}".format(
                        get_product_price(products_map[product_field_name]).price
                    ),
                    "name": products_map[product_field_name].name,
                }
        infos["shares"] = shares

        total_price = sum(
            map(
                lambda i: i["amount"] * float(i["price"]),
                shares.values(),
            )
        )
        infos["has_shares"] = total_price > 0
        infos["total"] = "{:.2f}".format(total_price)
        self.total_monthly += total_price

        return infos
