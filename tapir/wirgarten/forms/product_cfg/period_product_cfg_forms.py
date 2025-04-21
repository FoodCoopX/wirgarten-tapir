from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.utils.forms import DateInput
from tapir.wirgarten.constants import NO_DELIVERY, DeliveryCycle
from tapir.wirgarten.models import (
    GrowingPeriod,
    Product,
    ProductCapacity,
    ProductPrice,
    ProductType,
    TaxRate,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import get_next_contract_start_date
from tapir.wirgarten.utils import get_today
from tapir.wirgarten.validators import (
    validate_date_range,
    validate_growing_period_overlap,
)

KW_PROD_ID = "prodId"
KW_CAPACITY_ID = "capacityId"
KW_PERIOD_ID = "periodId"


class ProductTypeForm(forms.Form):
    template_name = "wirgarten/product/product_type_form.html"

    def __init__(self, *args, **kwargs):
        super(ProductTypeForm, self).__init__(*args)
        initial_name = ""
        initial_delivery_cycle = NO_DELIVERY
        initial_tax_rate = 0
        initial_capacity = 0.0
        product_type = None
        initial_notice_period = get_parameter_value(
            Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        )

        if KW_PERIOD_ID in kwargs:
            initial_period_id = kwargs[KW_PERIOD_ID]

            if KW_CAPACITY_ID in kwargs:  # update existing product type
                self.capacity = ProductCapacity.objects.get(id=kwargs[KW_CAPACITY_ID])
                initial_capacity = self.capacity.capacity
                product_type = ProductType.objects.get(id=self.capacity.product_type.id)

                try:
                    self.tax_rate = TaxRate.objects.get(
                        product_type=product_type, valid_to=None
                    )
                    initial_tax_rate = self.tax_rate.tax_rate
                except TaxRate.DoesNotExist:
                    initial_tax_rate = 0.19  # FIXME: default value in tapir paramenter

                initial_name = product_type.name
                initial_delivery_cycle = product_type.delivery_cycle
                initial_notice_period = NoticePeriodManager.get_notice_period_duration(
                    product_type=product_type, growing_period=self.capacity.period
                )

            else:  # create NEW -> lets choose from existing product types
                prod_types_without_capacity = [(None, _("--- Neu anlegen ---"))]
                prod_types_without_capacity.extend(
                    list(
                        map(
                            lambda pt: (pt.id, _(pt.name)),
                            ProductType.objects.exclude(
                                id__in=ProductCapacity.objects.filter(
                                    period__id=initial_period_id
                                ).values("product_type__id")
                            ),
                        )
                    )
                )

                self.fields["product_type"] = forms.ChoiceField(
                    choices=prod_types_without_capacity, required=False
                )

        self.fields["name"] = forms.CharField(
            initial=initial_name, required=False, label=_("Produkt Name")
        )
        self.fields["icon_link"] = forms.CharField(
            required=False,
            label=_("Icon Link"),
            initial=product_type.icon_link if product_type is not None else "",
        )
        self.fields["contract_link"] = forms.CharField(
            required=False,
            label=_("Link zu den Vertragsgrundsätzen"),
            initial=product_type.contract_link if product_type is not None else "",
        )
        self.fields["capacity"] = forms.FloatField(
            initial=initial_capacity,
            required=True,
            label=_("Produkt Kapazität (in Produkt-Größe)"),
        )
        self.fields["delivery_cycle"] = forms.ChoiceField(
            initial=initial_delivery_cycle,
            required=True,
            label=_("Liefer-/Abholzyklus"),
            choices=DeliveryCycle,
        )
        if get_parameter_value(Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL):
            self.fields["notice_period"] = forms.IntegerField(
                initial=initial_notice_period,
                required=True,
                label=_("Kündigungsfrist"),
                help_text=_("Anzahl an Monate"),
            )

        self.fields["tax_rate"] = forms.FloatField(
            initial=initial_tax_rate,
            required=True,
            label=_("Mehrwertsteuersatz"),  # FIXME: format
        )

        if product_type is not None:
            next_month = get_today() + relativedelta(day=1, months=1)
            self.fields["tax_rate_change_date"] = forms.DateField(
                required=True,
                label=_("Neuer Mehrwertsteuersatz gültig ab"),
                widget=DateInput(),
                initial=next_month,
            )

        self.fields["single_subscription_only"] = forms.BooleanField(
            required=False,
            label=_("Nur Einzelabonnement möglich"),
            initial=(
                product_type.single_subscription_only
                if product_type is not None
                else False
            ),
        )
        self.fields["is_affected_by_jokers"] = forms.BooleanField(
            initial=product_type.is_affected_by_jokers if product_type else True,
            required=False,
            label=_("Nimmt am Joker-Verfahren teil"),
        )


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

        today = get_today()
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
                    new_start_date = get_next_contract_start_date(ref_date=today)
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
