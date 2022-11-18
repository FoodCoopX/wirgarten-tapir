from importlib.resources import _

from django import forms

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import HarvestShareProduct, Product, ProductType
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_active_product_types


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

        harvest_share_products = {
            """harvest_shares_{variation}""".format(
                variation=p.product_ptr.name.lower()
            ): p.__dict__
            for p in HarvestShareProduct.objects.all()
        }

        for key, val in initial["harvest_shares"].items():
            if key.startswith("harvest_shares"):
                self.harvest_shares[key] = {
                    "amount": val,
                    "price": "{:.2f}".format(harvest_share_products[key]["price"]),
                    "name": _(harvest_share_products[key]["name"] + "-Ernteanteile"),
                }
            else:
                self.harvest_shares_info[key] = val

        harvest_shares_total = sum(
            map(lambda i: i["amount"] * float(i["price"]), self.harvest_shares.values())
        )

        solidarity_price = self.harvest_shares_info.get("solidarity_price", 0)

        self.total_monthly = harvest_shares_total * (1 + float(solidarity_price))

        self.harvest_shares_info["start_date"] = start_date
        self.harvest_shares_info["end_date"] = end_date

        self.harvest_shares_info["has_shares"] = harvest_shares_total > 0
        self.harvest_shares_info["total_without_solidarity"] = "{:.2f}".format(
            harvest_shares_total
        )
        self.harvest_shares_info["total"] = "{:.2f}".format(
            harvest_shares_total * (1 + float(solidarity_price))
        )
        self.harvest_shares_info["solidarity_price_diff"] = "{:+.2f}".format(
            float(harvest_shares_total) * float(solidarity_price)
        ).replace("+", "+ ")

        if "pickup_location" in initial:
            self.pickup_location = """{val.name}<br/>{val.street}, {val.postcode} {val.city}<br/>({val.info})""".format(
                val=initial["pickup_location"]["pickup_location"]
            )  # get pickup location text

        coop_shares_amount = initial["coop_shares"]["cooperative_shares"]
        coop_share_price = get_parameter_value(Parameter.COOP_SHARE_PRICE)
        self.total_onetime = coop_shares_amount * coop_share_price

        self.coop_shares = {
            "amount": coop_shares_amount,
            "price": "{:.2f}".format(coop_share_price),
            "total": "{:.2f}".format(coop_share_price * coop_shares_amount),
            "statute_link": get_parameter_value(Parameter.COOP_STATUTE_LINK),
        }

        self.chicken_shares_info = dict({"has_shares": False, "start_date": start_date})
        if "additional_shares" in initial:
            chicken_share_products = {
                """chicken_shares_{variation}""".format(variation=p.name): p.__dict__
                for p in Product.objects.filter(
                    type=ProductType.objects.get(name="Hühneranteile")
                )
            }
            self.chicken_shares = dict()
            for key, val in initial["additional_shares"].items():
                if key.startswith("chicken_shares"):
                    self.chicken_shares[key] = {
                        "amount": val,
                        "price": "{:.2f}".format(chicken_share_products[key]["price"]),
                        "name": _(
                            chicken_share_products[key]["name"] + " Hühneranteile"
                        ),
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
                Product.objects.get(
                    type=get_active_product_types().get(name="BestellCoop")
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
