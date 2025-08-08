from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.forms import DateInput
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.models import (
    GrowingPeriod,
    Product,
    ProductCapacity,
    ProductPrice,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today
from tapir.wirgarten.validators import (
    validate_date_range,
    validate_growing_period_overlap,
)

KW_PROD_ID = "prodId"
KW_CAPACITY_ID = "capacityId"
KW_PERIOD_ID = "periodId"


class ProductForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args)

        self.capacity_id = kwargs[KW_CAPACITY_ID]
        self.type_id = ProductCapacity.objects.get(id=self.capacity_id).product_type_id

        initial_id = "-"
        initial_name = ""
        initial_price = 0
        initial_size = 1

        if KW_PROD_ID in kwargs:
            initial_id = kwargs[KW_PROD_ID]
            product = Product.objects.get(id=initial_id)
            prices = ProductPrice.objects.filter(product=product).order_by(
                "-valid_from"
            )
            initial_name = product.name

            period = GrowingPeriod.objects.get(id=kwargs[KW_PERIOD_ID])
            for price in prices:
                if price.valid_from < period.end_date:
                    initial_price = price.price
                    initial_size = price.size

        self.fields["id"] = forms.CharField(
            initial=initial_id, widget=forms.HiddenInput()
        )
        self.fields["name"] = forms.CharField(
            initial=initial_name, required=True, label=_("Produkt Name")
        )
        self.fields["price"] = forms.FloatField(
            initial=initial_price, required=True, label=_("Preis")
        )
        self.fields["size"] = forms.FloatField(
            initial=initial_size, required=True, label=_("Größe")
        )
        self.fields["base"] = forms.BooleanField(
            initial=False, required=False, label=_("Basisprodukt")
        )

    def is_valid(self, *args, **kwargs):
        super(ProductForm, self).is_valid(*args, **kwargs)

        if not self.cleaned_data["base"]:
            if not Product.objects.filter(type_id=self.type_id, base=True).exists():
                self.add_error(
                    field="base",
                    error=ValidationError(_("Bitte lege zuerst ein Basisprodukt an.")),
                )

        return not self.errors


class GrowingPeriodForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(GrowingPeriodForm, self).__init__(*args)
        self.cache = {}

        today = get_today(cache=self.cache)
        initial = {
            "id": "-",
            "start_date": today + relativedelta(days=1),
            "end_date": today + relativedelta(years=1),
        }

        if KW_PERIOD_ID in kwargs:
            period = GrowingPeriod.objects.get(id=kwargs[KW_PERIOD_ID])
            new_start_date = period.end_date + relativedelta(days=1)
            self.update_initial(initial, new_start_date)
            initial["id"] = period.id
        else:
            try:
                period = GrowingPeriod.objects.order_by("-end_date")
                if period.exists():
                    period = period[:1][0]
                    new_start_date = period.end_date + relativedelta(days=1)
                else:
                    new_start_date = get_first_of_next_month(date=today)
                self.update_initial(initial, new_start_date)
            except GrowingPeriod.DoesNotExist:
                pass

        self.fields["id"] = forms.CharField(
            initial=initial["id"], required=False, widget=forms.HiddenInput()
        )
        self.fields["start_date"] = forms.DateField(
            required=True,
            label=_("Von"),
            widget=DateInput(),
            initial=initial["start_date"],
        )
        self.fields["end_date"] = forms.DateField(
            required=True,
            label=_("Bis"),
            widget=DateInput(),
            initial=initial["end_date"],
        )
        if get_parameter_value(ParameterKeys.JOKERS_ENABLED, cache=self.cache):
            self.fields["max_jokers_per_member"] = forms.BooleanField(
                required=False,
                label=_("Maximal Anzahl an Joker per Mitglied"),
                initial=4,
            )

    def is_valid(self):
        super(GrowingPeriodForm, self).is_valid()

        start = self.cleaned_data["start_date"]
        end = self.cleaned_data["end_date"]

        error_field = "start_date"

        try:
            validate_date_range(start_date=start, end_date=end)
        except ValidationError as e:
            self.add_error(field=error_field, error=e)

        try:
            validate_growing_period_overlap(start_date=start, end_date=end)
        except ValidationError as e:
            self.add_error(field=error_field, error=e)

        return not self.has_error(field=error_field)

    def update_initial(self, initial, new_start_date):
        initial.update(
            {
                "start_date": new_start_date,
                "end_date": new_start_date + relativedelta(years=1, days=-1),
            }
        )
