from datetime import date
from importlib.resources import _

from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.clickjacking import xframe_options_exempt
from formtools.wizard.views import CookieWizardView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.forms.member.forms import PersonalDataForm
from tapir.wirgarten.forms.pickup_location import PickupLocationChoiceForm
from tapir.wirgarten.forms.registration.bestellcoop import BestellCoopForm
from tapir.wirgarten.forms.registration.chicken_shares import ChickenShareForm
from tapir.wirgarten.forms.registration.consents import ConsentForm
from tapir.wirgarten.forms.registration.coop_shares import CooperativeShareForm
from tapir.wirgarten.forms.registration.empty_form import EmptyForm
from tapir.wirgarten.forms.registration.harvest_shares import HarvestShareForm
from tapir.wirgarten.forms.registration.payment_data import PaymentDataForm
from tapir.wirgarten.forms.registration.summary import SummaryForm
from tapir.wirgarten.models import (
    Subscription,
    ProductType,
    Product,
    GrowingPeriod,
    Member,
    MandateReference,
    ProductPrice,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import (
    create_mandate_ref,
    create_member,
    buy_cooperative_shares,
    get_next_contract_start_date,
)
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_free_product_capacity,
)

# Wizard Steps Keys
STEP_HARVEST_SHARES = "Harvest Shares"
STEP_NO_HARVEST_SHARES_AVAILABLE = "No Harvest Shares Available"
STEP_COOP_SHARES = "Cooperative Shares"
STEP_NO_COOP_SHARES_AVAILABLE = "No Cooperative Shares Available"
STEP_ADDITIONAL_SHARES = "Additional Shares"
STEP_BESTELLCOOP = "BestellCoop"
STEP_PICKUP_LOCATION = "Pickup Location"
STEP_SUMMARY = "Summary"
STEP_PERSONAL_DETAILS = "Personal Details"
STEP_PAYMENT_DETAILS = "Payment Details"
STEP_CONSENTS = "Consent"

FORM_TITLES = {
    STEP_HARVEST_SHARES: _("Ernteanteile"),
    STEP_NO_HARVEST_SHARES_AVAILABLE: _("Ernteanteile"),
    STEP_COOP_SHARES: _("Genossenschaft"),
    STEP_NO_COOP_SHARES_AVAILABLE: _("Genossenschaft"),
    STEP_ADDITIONAL_SHARES: _("Zusatzabos"),
    STEP_BESTELLCOOP: _("BestellCoop"),
    STEP_PICKUP_LOCATION: _("Abholort"),
    STEP_SUMMARY: _("Übersicht"),
    STEP_PERSONAL_DETAILS: _("Persönliche Daten"),
    STEP_PAYMENT_DETAILS: _("Zahlung"),
    STEP_CONSENTS: _("Widerruf & Datenschutz"),
}

FORMS = [
    (STEP_HARVEST_SHARES, HarvestShareForm),
    (STEP_NO_HARVEST_SHARES_AVAILABLE, EmptyForm),
    (STEP_COOP_SHARES, CooperativeShareForm),
    (STEP_NO_COOP_SHARES_AVAILABLE, EmptyForm),
    (STEP_ADDITIONAL_SHARES, ChickenShareForm),
    (STEP_BESTELLCOOP, BestellCoopForm),
    (STEP_PICKUP_LOCATION, PickupLocationChoiceForm),
    (STEP_SUMMARY, SummaryForm),
    (STEP_PERSONAL_DETAILS, PersonalDataForm),
    (STEP_PAYMENT_DETAILS, PaymentDataForm),
    (STEP_CONSENTS, ConsentForm),
]


def is_product_type_available(product_type: ProductType) -> bool:
    return get_free_product_capacity(
        product_type_id=product_type.id
    ) > get_cheapest_product_price(product_type)


def get_cheapest_product_price(product_type: ProductType):
    today = date.today()
    return (
        ProductPrice.objects.filter(product__type=product_type, valid_from__lte=today)
        .order_by("price")
        .values("price")[0:1][0]["price"]
    )


def show_bestellcoop() -> bool:
    param = get_parameter_value(Parameter.BESTELLCOOP_SUBSCRIBABLE)
    return param == 1 or (
        param == 2
        and is_product_type_available(
            get_active_product_types().get(name="BestellCoop")
        )
    )


def show_chicken_shares() -> bool:
    param = get_parameter_value(Parameter.CHICKEN_SHARES_SUBSCRIBABLE)
    return param == 1 or (
        param == 2
        and is_product_type_available(
            get_active_product_types().get(name="Hühneranteile")
        )
    )


def show_harvest_shares(wizard=None) -> bool:
    param = get_parameter_value(Parameter.HARVEST_SHARES_SUBSCRIBABLE)
    return param == 1 or (
        param == 2
        and is_product_type_available(
            get_active_product_types().get(name="Ernteanteile")
        )
    )


def dont_show_harvest_shares(wizard=None) -> bool:
    return not show_harvest_shares(wizard)


def has_selected_harvest_shares(wizard) -> bool:
    if (
        "step_data" in wizard.storage.data
        and STEP_HARVEST_SHARES in wizard.storage.data["step_data"]
    ):
        for key, val in wizard.storage.data["step_data"][STEP_HARVEST_SHARES].items():
            if key.startswith("Harvest Shares-harvest_shares_") and int(val[0]) > 0:
                return True
        return False


def show_coop_shares(x):
    return get_parameter_value(
        Parameter.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES
    ) or has_selected_harvest_shares(x)


def dont_show_coop_shares(x):
    return not show_coop_shares(x)


CONDITIONS = {
    STEP_HARVEST_SHARES: show_harvest_shares,
    STEP_NO_HARVEST_SHARES_AVAILABLE: dont_show_harvest_shares,
    STEP_COOP_SHARES: show_coop_shares,
    STEP_NO_COOP_SHARES_AVAILABLE: dont_show_coop_shares,
    STEP_ADDITIONAL_SHARES: lambda x: has_selected_harvest_shares(x)
    and show_chicken_shares(),
    STEP_BESTELLCOOP: lambda x: has_selected_harvest_shares(x) and show_bestellcoop(),
    STEP_PICKUP_LOCATION: has_selected_harvest_shares,
}


def save_subscriptions(
    form_dict,
    member: Member,
    start_date: date,
    end_date: date,
    growing_period: GrowingPeriod,
):
    mandate_ref = create_mandate_ref(member, False)
    product_type = ProductType.objects.get(name=ProductTypes.HARVEST_SHARES)
    has_shares = False
    for key, quantity in form_dict[STEP_HARVEST_SHARES].cleaned_data.items():
        if key.startswith("harvest_shares_") and quantity > 0:
            product = Product.objects.get(
                type=product_type, name=key.replace("harvest_shares_", "").upper()
            )
            Subscription.objects.create(
                member=member,
                product=product,
                period=growing_period,
                quantity=quantity,
                start_date=start_date,
                end_date=end_date,
                solidarity_price=form_dict[STEP_HARVEST_SHARES].cleaned_data[
                    "solidarity_price"
                ],
                mandate_ref=mandate_ref,
            )
            has_shares = True

    if has_shares:
        save_additional_shares(
            form_dict, member, start_date, end_date, growing_period, mandate_ref
        )
        save_bestellcoop(
            form_dict, member, start_date, end_date, growing_period, mandate_ref
        )


def save_member(form_dict):
    member = form_dict[STEP_PERSONAL_DETAILS].instance

    if STEP_PICKUP_LOCATION in form_dict:
        member.pickup_location = form_dict[STEP_PICKUP_LOCATION].cleaned_data[
            "pickup_location"
        ]
    member.account_owner = form_dict[STEP_PAYMENT_DETAILS].cleaned_data["account_owner"]
    member.iban = form_dict[STEP_PAYMENT_DETAILS].cleaned_data["iban"]
    member.bic = form_dict[STEP_PAYMENT_DETAILS].cleaned_data["bic"]
    member.is_active = False

    now = date.today()
    member.sepa_consent = now
    member.withdrawal_consent = now
    member.privacy_consent = now

    return create_member(member)


def save_additional_shares(
    form_dict,
    member: Member,
    start_date: date,
    end_date: date,
    growing_period: GrowingPeriod,
    mandate_ref: MandateReference,
):
    product_type = ProductType.objects.get(name=ProductTypes.CHICKEN_SHARES)
    for key, quantity in form_dict[STEP_ADDITIONAL_SHARES].cleaned_data.items():
        if quantity > 0 and key.startswith("chicken_shares_"):
            product = Product.objects.get(
                type=product_type, name=key.replace("chicken_shares_", "")
            )
            Subscription.objects.create(
                member=member,
                product=product,
                quantity=quantity,
                period=growing_period,
                start_date=start_date,
                end_date=end_date,
                mandate_ref=mandate_ref,
            )


def save_bestellcoop(
    form_dict,
    member,
    start_date: date,
    end_date: date,
    growing_period: GrowingPeriod,
    mandate_ref: MandateReference,
):
    if form_dict[STEP_BESTELLCOOP].cleaned_data["bestellcoop"]:
        product = Product.objects.get(
            type=get_active_product_types().get(name=ProductTypes.BESTELLCOOP)
        )

        Subscription.objects.create(
            member=member,
            product=product,
            quantity=1,
            start_date=start_date,
            end_date=end_date,
            period=growing_period,
            mandate_ref=mandate_ref,
        )


@method_decorator(xframe_options_exempt, name="dispatch")
@method_decorator(xframe_options_exempt, name="post")
class RegistrationWizardView(CookieWizardView):
    template_name = "wirgarten/registration/registration_wizard.html"
    form_list = FORMS
    condition_dict = CONDITIONS

    finish_button_label = _("Bestellung abschließen")

    def __init__(self, *args, **kwargs):
        super(RegistrationWizardView, self).__init__(*args, **kwargs)

        self.start_date = get_next_contract_start_date()
        self.growing_period = GrowingPeriod.objects.filter(
            start_date__lte=self.start_date, end_date__gte=self.start_date
        ).first()
        self.end_date = self.growing_period.end_date

    def has_step(self, step):
        return step in self.storage.data["step_data"]

    def get_template_names(self):
        if self.steps.current == STEP_NO_HARVEST_SHARES_AVAILABLE:
            return ["wirgarten/registration/steps/harvest_shares_no_subscription.html"]
        elif self.steps.current == STEP_NO_COOP_SHARES_AVAILABLE:
            return ["wirgarten/registration/steps/coop_shares_not_available.html"]
        elif self.steps.current == STEP_SUMMARY:
            return ["wirgarten/registration/steps/summary.html"]
        return ["wirgarten/registration/registration_form.html"]

    # gather data from dependent forms
    def get_form_initial(self, step=None):
        initial = self.initial_dict
        if step == STEP_COOP_SHARES:
            if self.has_step(STEP_HARVEST_SHARES):
                data = self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
                for key, val in data.items():
                    initial[key] = val
        elif step == STEP_PICKUP_LOCATION:
            # TODO: has to be implemented with product_type.id not name when the wizard generically handles all products
            initial["product_types"] = []
            if self.has_step(STEP_HARVEST_SHARES) and is_harvest_shares_selected(
                self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
            ):
                initial["product_types"].append("Ernteanteile")
            if self.has_step(STEP_ADDITIONAL_SHARES) and is_chicken_shares_selected(
                self.get_cleaned_data_for_step(STEP_ADDITIONAL_SHARES)
            ):
                initial["product_types"].append("Hühneranteile")
        elif step == STEP_SUMMARY:
            initial["general"] = {
                "start_date": self.start_date,
                "end_date": self.end_date,
            }
            if self.has_step(STEP_HARVEST_SHARES):
                initial["harvest_shares"] = self.get_cleaned_data_for_step(
                    STEP_HARVEST_SHARES
                )

                if is_harvest_shares_selected(
                    self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
                ):
                    if self.has_step(STEP_ADDITIONAL_SHARES):
                        initial["additional_shares"] = self.get_cleaned_data_for_step(
                            STEP_ADDITIONAL_SHARES
                        )
                    if self.has_step(STEP_BESTELLCOOP):
                        initial["bestellcoop"] = self.get_cleaned_data_for_step(
                            STEP_BESTELLCOOP
                        )
                    initial["pickup_location"] = self.get_cleaned_data_for_step(
                        STEP_PICKUP_LOCATION
                    )
            else:
                initial["harvest_shares"] = {}

            initial["coop_shares"] = (
                self.get_cleaned_data_for_step(STEP_COOP_SHARES)
                if self.has_step(STEP_COOP_SHARES)
                else {"cooperative_shares": 0}
            )

        return initial

    @transaction.atomic
    def done(self, form_list, form_dict, **kwargs):
        member = save_member(form_dict)

        if STEP_HARVEST_SHARES in form_dict and is_harvest_shares_selected(
            form_dict[STEP_HARVEST_SHARES].cleaned_data
        ):
            save_subscriptions(
                form_dict,
                member,
                self.start_date,
                self.end_date,
                self.growing_period,
            )

        # coop membership starts after the cancellation period, so I call get_next_start_date() to add 1 month
        actual_coop_start = get_next_contract_start_date(self.start_date)
        buy_cooperative_shares(
            form_dict[STEP_COOP_SHARES].cleaned_data["cooperative_shares"],
            member,
            actual_coop_start,
        )

        return HttpResponseRedirect(
            reverse_lazy("wirgarten:draftuser_confirm_registration")
        )


@method_decorator(xframe_options_exempt, name="dispatch")
class RegistrationWizardConfirmView(generic.TemplateView):
    template_name = "wirgarten/registration/confirmation.html"


def is_harvest_shares_selected(harvest_share_form_data):
    for key, val in harvest_share_form_data.items():
        if key.startswith("harvest_shares_") and val > 0:
            return True
    return False


def is_chicken_shares_selected(chicken_share_form_data):
    for key, val in chicken_share_form_data.items():
        if key.startswith("chicken_shares_") and val > 0:
            return True
    return False
