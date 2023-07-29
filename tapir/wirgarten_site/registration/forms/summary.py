from django import forms
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta

from tapir import settings
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import (
    ProductTypes,
    DeliveryCycleDict,
)
from tapir.wirgarten.forms.subscription import BASE_PRODUCT_FIELD_PREFIX
from tapir.wirgarten.models import HarvestShareProduct, Product, ProductType
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import get_next_delivery_date_for_product_type
from tapir.wirgarten.service.products import (
    get_product_price,
)


class SummaryForm(forms.Form):
    def is_valid(self):
        return True

    def __init__(self, *args, **kwargs):
        super(SummaryForm, self).__init__(*args, **kwargs)
        initial = kwargs["initial"]

        start_date = initial["general"]["start_date"]
        end_date = initial["general"]["end_date"]

        # prepare data for the summary template
        self.harvest_shares = dict()
        self.harvest_shares_info = dict()

        base_type = ProductType.objects.get(
            id=get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        )

        harvest_share_products = {
            f"{BASE_PRODUCT_FIELD_PREFIX}{p.product_ptr.name}": p
            for p in list(
                HarvestShareProduct.objects.filter(deleted=False, type=base_type)
            )
        }

        for key, val in initial["base_product"].items():
            if key.startswith("base_product"):
                self.harvest_shares[key] = {
                    "amount": val,
                    "price": "{:.2f}".format(
                        get_product_price(harvest_share_products[key], start_date).price
                    ),
                    "name": _(harvest_share_products[key].name + "-" + base_type.name),
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
            base_type.delivery_cycle
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

        self.harvest_shares_info[
            "first_delivery_date"
        ] = get_next_delivery_date_for_product_type(
            base_type, start_date
        ) + relativedelta(
            days=delivery_date_offset
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
            "statute_link": get_parameter_value(Parameter.COOP_STATUTE_LINK),
        }

        chicken_shares_type = ProductType.objects.get(name=ProductTypes.CHICKEN_SHARES)
        self.chicken_shares_info = dict(
            {
                "has_shares": False,
                "start_date": start_date,
                "delivery_interval": DeliveryCycleDict[
                    chicken_shares_type.delivery_cycle
                ],
                "first_delivery_date": get_next_delivery_date_for_product_type(
                    chicken_shares_type, start_date
                )
                + relativedelta(days=delivery_date_offset),
            }
        )
        if "additional_shares" in initial:
            chicken_share_products = {
                f"{p.type_id}_{p.name}": p
                for p in Product.objects.filter(type=chicken_shares_type)
            }
            self.chicken_shares = dict()
            for key, val in initial["additional_shares"][
                "additional_product_Hühneranteile"
            ].items():
                if key in chicken_share_products:
                    self.chicken_shares[key] = {
                        "amount": val,
                        "price": "{:.2f}".format(
                            get_product_price(chicken_share_products[key]).price
                        ),
                        "name": _(chicken_share_products[key].name + " Hühneranteile"),
                    }

            chicken_total = sum(
                map(
                    lambda i: i["amount"] * float(i["price"]),
                    self.chicken_shares.values(),
                )
            )
            self.chicken_shares_info["has_shares"] = chicken_total > 0
            self.chicken_shares_info["total"] = "{:.2f}".format(chicken_total)
            self.total_monthly += chicken_total

        self.bestellcoop = {"sign_up": False}
        if "bestellcoop" in initial:
            price = float(
                get_product_price(
                    Product.objects.filter(
                        type__name=ProductTypes.BESTELLCOOP, deleted=False
                    )[0]
                ).price
            )  # FIXME: name must be configurable
            sign_up = initial["bestellcoop"]["bestellcoop"]
            self.bestellcoop["sign_up"] = sign_up
            self.bestellcoop["price"] = "{:.2f}".format(price)
            self.bestellcoop["start_date"] = start_date
            if sign_up:
                self.total_monthly += price

        self.total_monthly = "{:.2f}".format(self.total_monthly)
        self.total_onetime = "{:.2f}".format(self.total_onetime)

        self.has_additional_shares = self.harvest_shares_info["has_shares"] and (
            self.chicken_shares_info["has_shares"] or self.bestellcoop["sign_up"]
        )
