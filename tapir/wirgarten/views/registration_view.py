from datetime import date
from importlib.resources import _

from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.clickjacking import xframe_options_exempt
from formtools.wizard.views import CookieWizardView

from tapir.accounts.models import LdapPerson
from tapir.wirgarten.forms.registration.bestellcoop import BestellCoopForm
from tapir.wirgarten.forms.registration.chicken_shares import ChickenShareForm
from tapir.wirgarten.forms.registration.consents import ConsentForm
from tapir.wirgarten.forms.registration.coop_shares import CooperativeShareForm
from tapir.wirgarten.forms.registration.harvest_shares import HarvestShareForm
from tapir.wirgarten.forms.registration.payment_data import PaymentDataForm
from tapir.wirgarten.forms.registration.personal_data import PersonalDataForm
from tapir.wirgarten.forms.registration.pickup_location import PickupLocationForm
from tapir.wirgarten.forms.registration.summary import SummaryForm
from tapir.wirgarten.models import ActiveProduct

# Wizard Steps Keys
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


def save_active_products(form_dict, member):
    for key, amount in form_dict[STEP_HARVEST_SHARES].cleaned_data.items():
        if key.startswith("harvest_shares_") and amount > 0:
            ActiveProduct.objects.create(
                member=member,
                type="HarvestShare",
                variant=key.replace("harvest_shares_", ""),
                amount=amount,
                start_date=date.today(),  # FIXME real start date
                end_date=date.today(),  # FIXME real end date
            )

            # only save additional products if the applicant has selected at least 1 harvest share
            save_additional_shares(form_dict, member)
            save_bestellcoop(form_dict, member)


def save_member(form_dict):
    member = form_dict[STEP_PERSONAL_DETAILS].instance

    member.solidarity_price = form_dict[STEP_HARVEST_SHARES].cleaned_data[
        "solidarity_price"
    ]
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


def save_additional_shares(form_dict, member):
    for key, amount in form_dict[STEP_ADDITIONAL_SHARES].cleaned_data.items():
        if amount > 0 and key.startswith("chicken_shares_"):
            ActiveProduct.objects.create(
                member=member,
                type="ChickenShare",
                variant=key.replace("chicken_shares_", ""),
                amount=amount,
                start_date=date.today(),  # FIXME real start date
                end_date=date.today(),  # FIXME real end date
            )


def save_cooperative_shares(form_dict, member):
    ActiveProduct.objects.create(
        member=member,
        type="CoopShare",
        amount=form_dict[STEP_COOP_SHARES].cleaned_data["cooperative_shares"],
        start_date=date.today(),  # FIXME real start date
        end_date=date.today(),  # FIXME real end date
    )


def save_bestellcoop(form_dict, member):
    if form_dict[STEP_BESTELLCOOP].cleaned_data["bestellcoop"]:
        ActiveProduct.objects.create(
            member=member,
            type="BestellCoop",
            amount=1,
            start_date=date.today(),  # FIXME real start date
            end_date=date.today(),  # FIXME real end date
        )


@method_decorator(xframe_options_exempt, name="dispatch")
@method_decorator(xframe_options_exempt, name="post")
class RegistrationWizardView(CookieWizardView):
    template_name = "wirgarten/registration/registration_wizard.html"
    form_list = FORMS

    finish_button_label = _("Bestellung abschließen")

    def get_template_names(self):
        if self.steps.current == "Summary":
            return ["wirgarten/registration/steps/summary.html"]
        else:
            return ["wirgarten/registration/registration_form.html"]

    def no_harvest_shares_selected(self):
        for key, val in self.get_cleaned_data_for_step(STEP_HARVEST_SHARES).items():
            if key.startswith("harvest_shares_"):
                if val > 0:
                    return False
        return True

    # skip certain steps if no harvest shares are selected
    def override_next_step(self, next_step, overridden):
        if (
            next_step == STEP_ADDITIONAL_SHARES or next_step == STEP_BESTELLCOOP
        ) and self.no_harvest_shares_selected():
            return overridden

        return next_step

    # gather data from dependent forms
    def get_form_initial(self, step=None):
        initial = self.initial_dict
        if step == STEP_COOP_SHARES:
            data = self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
            for key, val in data.items():
                initial[key] = val
        elif step == STEP_SUMMARY:
            initial["harvest_shares"] = self.get_cleaned_data_for_step(
                STEP_HARVEST_SHARES
            )
            initial["coop_shares"] = self.get_cleaned_data_for_step(STEP_COOP_SHARES)
            initial["additional_shares"] = self.get_cleaned_data_for_step(
                STEP_ADDITIONAL_SHARES
            )
            initial["bestellcoop"] = self.get_cleaned_data_for_step(STEP_BESTELLCOOP)
            initial["pickup_location"] = self.get_cleaned_data_for_step(
                STEP_PICKUP_LOCATION
            )
        return initial

    def get_prev_step(self, step=None):
        prev_step = super(RegistrationWizardView, self).get_prev_step()
        return self.override_next_step(prev_step, STEP_COOP_SHARES)

    def get_next_step(self, step=None):
        next_step = super(RegistrationWizardView, self).get_next_step()
        return self.override_next_step(next_step, STEP_SUMMARY)

    @transaction.atomic
    def done(self, form_list, form_dict, **kwargs):
        # TODO: these fields are still missing:
        #  - Mandatsreferenzen (für alle Produkte einzeln?)
        #  - Geeichtes Startdatum (bzw. unterjährig falls zugelassen)
        #  - Enddatum
        #  - Fälligkeitsdatum

        member = save_member(form_dict)

        save_active_products(form_dict, member)
        save_cooperative_shares(form_dict, member)

        return HttpResponseRedirect(
            reverse_lazy("wirgarten:draftuser_confirm_registration")
        )


@method_decorator(xframe_options_exempt, name="dispatch")
class RegistrationWizardConfirmView(generic.TemplateView):
    template_name = "wirgarten/registration/confirmation.html"
