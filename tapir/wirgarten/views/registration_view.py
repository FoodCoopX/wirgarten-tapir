from datetime import date, datetime
from importlib.resources import _

from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.clickjacking import xframe_options_exempt
from formtools.wizard.views import CookieWizardView
from nanoid import generate

from tapir.accounts.models import LdapPerson
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.forms.registration.bestellcoop import BestellCoopForm
from tapir.wirgarten.forms.registration.chicken_shares import ChickenShareForm
from tapir.wirgarten.forms.registration.consents import ConsentForm
from tapir.wirgarten.forms.registration.coop_shares import CooperativeShareForm
from tapir.wirgarten.forms.registration.harvest_shares import HarvestShareForm
from tapir.wirgarten.forms.registration.payment_data import PaymentDataForm
from tapir.wirgarten.forms.registration.personal_data import PersonalDataForm
from tapir.wirgarten.forms.registration.pickup_location import PickupLocationForm
from tapir.wirgarten.forms.registration.summary import SummaryForm
from tapir.wirgarten.models import (
    Subscription,
    ProductType,
    Product,
    GrowingPeriod,
    Member,
    ShareOwnership,
    MandateReference,
    Payment,
)

# Wizard Steps Keys
from tapir.wirgarten.parameters import Parameter

MANDATE_REF_ALPHABET = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

STEP_HARVEST_SHARES = "Harvest Shares"
STEP_COOP_SHARES = "Cooperative Shares"
STEP_ADDITIONAL_SHARES = "Additional Shares"
STEP_BESTELLCOOP = "BestellCoop"
STEP_PICKUP_LOCATION = "Pickup Location"
STEP_SUMMARY = "Summary"
STEP_PERSONAL_DETAILS = "Personal Details"
STEP_PAYMENT_DETAILS = "Payment Details"
STEP_CONSENTS = "Consent"

FORM_TITLES = {
    STEP_HARVEST_SHARES: _("Ernteanteile"),
    STEP_COOP_SHARES: _("Genossenschaft"),
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
    (STEP_COOP_SHARES, CooperativeShareForm),
    (STEP_ADDITIONAL_SHARES, ChickenShareForm),
    (STEP_BESTELLCOOP, BestellCoopForm),
    (STEP_PICKUP_LOCATION, PickupLocationForm),
    (STEP_SUMMARY, SummaryForm),
    (STEP_PERSONAL_DETAILS, PersonalDataForm),
    (STEP_PAYMENT_DETAILS, PaymentDataForm),
    (STEP_CONSENTS, ConsentForm),
]


def show_all_steps(wizard):
    if (
        "step_data" in wizard.storage.data
        and STEP_HARVEST_SHARES in wizard.storage.data["step_data"]
    ):
        for key, val in wizard.storage.data["step_data"][STEP_HARVEST_SHARES].items():
            if key.startswith("Harvest Shares-harvest_shares_") and int(val[0]) > 0:
                return True
        return False


CONDITIONS = {
    STEP_ADDITIONAL_SHARES: show_all_steps,
    STEP_BESTELLCOOP: show_all_steps,
    STEP_PICKUP_LOCATION: show_all_steps,
}

PRODUCT_TYPE_HARVEST_SHARES = "Ernteanteile"
PRODUCT_TYPE_CHICKEN_SHARES = "Hühneranteile"
PRODUCT_TYPE_BESTELLCOOP = "BestellCoop"


def save_subscriptions(
    form_dict,
    member: Member,
    start_date: date,
    end_date: date,
    growing_period: GrowingPeriod,
):
    mandate_ref = save_mandate_ref(member, False)
    product_type = ProductType.objects.get(name=PRODUCT_TYPE_HARVEST_SHARES)
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

    # FIXME: username must be guaranteed unique! Otherwise we get duplicate key error
    #  Do we even need a username? Why not login with email?
    member.username = member.first_name.lower() + "." + member.last_name.lower()

    save_ldap_person(member)

    member.save()
    return member


def save_ldap_person(member):
    if member.has_ldap():
        ldap_user = member.get_ldap()
    else:
        ldap_user = LdapPerson(uid=member.username)

    ldap_user.sn = member.last_name or member.username
    ldap_user.cn = member.get_full_name() or member.username
    ldap_user.mail = member.email
    ldap_user.save()


def save_additional_shares(
    form_dict,
    member: Member,
    start_date: date,
    end_date: date,
    growing_period: GrowingPeriod,
    mandate_ref: MandateReference,
):
    product_type = ProductType.objects.get(name=PRODUCT_TYPE_CHICKEN_SHARES)
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


def save_cooperative_shares(form_dict, member: Member, start_date):
    mandate_ref = save_mandate_ref(member, True)
    share_price = get_parameter_value(Parameter.COOP_SHARE_PRICE)
    quantity = form_dict[STEP_COOP_SHARES].cleaned_data["cooperative_shares"]
    due_date = start_date.replace(day=get_parameter_value(Parameter.PAYMENT_DUE_DAY))

    ShareOwnership.objects.create(
        member=member,
        quantity=quantity,
        share_price=share_price,
        entry_date=start_date,  # FIXME: entry_date must be the first day after the notice period!
        mandate_ref=mandate_ref,
    )

    Payment.objects.create(
        due_date=due_date,
        amount=share_price * quantity,
        mandate_ref=mandate_ref,
        status=Payment.PaymentStatus.DUE,
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
        product_type = ProductType.objects.get(name=PRODUCT_TYPE_BESTELLCOOP)
        product = Product.objects.get(type=product_type, name="Mitgliedschaft")

        Subscription.objects.create(
            member=member,
            product=product,
            quantity=1,
            start_date=start_date,
            end_date=end_date,
            period=growing_period,
            mandate_ref=mandate_ref,
        )


def get_next_start_date(ref_date=date.today()):
    now = ref_date
    y, m = divmod(now.year * 12 + now.month, 12)
    return date(y, m + 1, 1)


def save_mandate_ref(member: Member, coop_shares: bool):
    ref = generate_mandate_ref(member, coop_shares)
    return MandateReference.objects.create(
        ref=ref, member=member, start_ts=datetime.now()
    )


def generate_mandate_ref(member: Member, coop_shares: bool):
    if coop_shares:
        return (
            f"""{str(member.id).zfill(10)}/{generate(MANDATE_REF_ALPHABET, 19)}/GENO"""
        )
    else:
        return f"""{str(member.id).zfill(10)}/{generate(MANDATE_REF_ALPHABET, 24)}"""


@method_decorator(xframe_options_exempt, name="dispatch")
@method_decorator(xframe_options_exempt, name="post")
class RegistrationWizardView(CookieWizardView):
    template_name = "wirgarten/registration/registration_wizard.html"
    form_list = FORMS
    condition_dict = CONDITIONS

    finish_button_label = _("Bestellung abschließen")

    def __init__(self, *args, **kwargs):
        super(RegistrationWizardView, self).__init__(*args, **kwargs)

        self.start_date = get_next_start_date()
        self.growing_period = GrowingPeriod.objects.filter(
            start_date__lte=self.start_date, end_date__gte=self.start_date
        ).first()
        self.end_date = self.growing_period.end_date

    def get_template_names(self):
        if (
            self.steps.current == STEP_HARVEST_SHARES
            and not self.is_harvest_share_subscribable()
        ):
            return ["wirgarten/registration/steps/harvest_shares_no_subscription.html"]
        if self.steps.current == STEP_SUMMARY:
            return ["wirgarten/registration/steps/summary.html"]
        return ["wirgarten/registration/registration_form.html"]

    def harvest_share_subscribable_auto(self):
        # FIXME: implement automatism logic
        print(
            "Defaults to False. Function 'harvest_share_sbscribable_auto' not implemented yet."
        )
        return False

    def is_harvest_share_subscribable(self) -> bool:
        status = get_parameter_value(Parameter.HARVEST_SHARES_SUBSCRIBABLE)
        if status == 0:
            return False
        elif status == 1:
            return True

        return self.harvest_share_subscribable_auto()

    # gather data from dependent forms
    def get_form_initial(self, step=None):
        initial = self.initial_dict
        if step == STEP_COOP_SHARES:
            data = self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
            for key, val in data.items():
                initial[key] = val
        elif step == STEP_SUMMARY:
            initial["general"] = {
                "start_date": self.start_date,
                "end_date": self.end_date,
            }
            initial["harvest_shares"] = self.get_cleaned_data_for_step(
                STEP_HARVEST_SHARES
            )
            initial["coop_shares"] = self.get_cleaned_data_for_step(STEP_COOP_SHARES)

            # TODO: check if steps exists
            if is_harvest_shares_selected(
                self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
            ):
                initial["additional_shares"] = self.get_cleaned_data_for_step(
                    STEP_ADDITIONAL_SHARES
                )
                initial["bestellcoop"] = self.get_cleaned_data_for_step(
                    STEP_BESTELLCOOP
                )
                initial["pickup_location"] = self.get_cleaned_data_for_step(
                    STEP_PICKUP_LOCATION
                )
        return initial

    @transaction.atomic
    def done(self, form_list, form_dict, **kwargs):
        member = save_member(form_dict)

        if is_harvest_shares_selected(form_dict[STEP_HARVEST_SHARES].cleaned_data):
            save_subscriptions(
                form_dict,
                member,
                self.start_date,
                self.end_date,
                self.growing_period,
            )

        # coop membership starts after the cancellation period, so I call get_next_start_date() to add 1 month
        actual_coop_start = get_next_start_date(self.start_date)
        save_cooperative_shares(form_dict, member, actual_coop_start)

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
