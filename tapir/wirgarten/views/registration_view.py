from datetime import date

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.clickjacking import xframe_options_exempt
from formtools.wizard.views import CookieWizardView

from tapir import settings
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.forms.member.forms import (
    PersonalDataRegistrationForm,
    MarketingFeedbackForm,
)
from tapir.wirgarten.forms.pickup_location import PickupLocationChoiceForm
from tapir.wirgarten.forms.registration.bestellcoop import BestellCoopForm
from tapir.wirgarten.forms.registration.chicken_shares import ChickenShareForm
from tapir.wirgarten.forms.registration.coop_shares import CooperativeShareForm
from tapir.wirgarten.forms.registration.empty_form import EmptyForm
from tapir.wirgarten.forms.registration.harvest_shares import HarvestShareForm
from tapir.wirgarten.forms.registration.summary import SummaryForm
from tapir.wirgarten.models import (
    GrowingPeriod,
    MemberPickupLocation,
    Subscription,
    Product,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import (
    create_mandate_ref,
    buy_cooperative_shares,
    get_next_contract_start_date,
    send_order_confirmation,
)
from tapir.wirgarten.service.products import (
    is_harvest_shares_available,
    is_bestellcoop_available,
    is_chicken_shares_available,
    get_future_subscriptions,
)
from tapir.wirgarten.utils import get_now, get_today

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

FORM_TITLES = {
    STEP_HARVEST_SHARES: (
        _("Ernteanteile"),
        _("Erntevertrag - Wieviel Gemüse möchtest du jede Woche bekommen?"),
    ),
    STEP_NO_HARVEST_SHARES_AVAILABLE: (
        _("Ernteanteile"),
        _("Erntevertrag - Wieviel Gemüse möchtest du jede Woche bekommen?"),
    ),
    STEP_COOP_SHARES: (
        _("Genossenschaft"),
        _(
            "Genossenschaft - Mit wie vielen Genossenschaftsanteilen möchtest du dich an deinem WirGarten beteiligen?"
        ),
    ),
    STEP_NO_COOP_SHARES_AVAILABLE: (
        _("Genossenschaft"),
        _(
            "Genossenschaft - Mit wie vielen Genossenschaftsanteilen möchtest du dich an deinem WirGarten beteiligen?"
        ),
    ),
    STEP_ADDITIONAL_SHARES: (
        _("Zusatzabo"),
        _("Zusatzabo  - Willst du einen Hühneranteil mit Eiern?"),
    ),
    STEP_BESTELLCOOP: (
        _("BestellCoop"),
        _(
            "BestellCoop - Möchtest du regelmäßig Grundnahrungsmittel in großen Mengen bestellen?"
        ),
    ),
    STEP_PICKUP_LOCATION: (
        _("Abholort"),
        _("Abholort - Wo möchtest du dein Gemüse abholen?"),
    ),
    STEP_SUMMARY: (_("Übersicht"), _("Übersicht")),
    STEP_PERSONAL_DETAILS: (
        _("Persönliche Daten"),
        _("Vertragsabschluss - Jetzt fehlen nur noch deine persönlichen Daten!"),
    ),
}


def has_selected_harvest_shares(wizard) -> bool:
    if (
        "step_data" in wizard.storage.data
        and STEP_HARVEST_SHARES in wizard.storage.data["step_data"]
    ):
        for key, val in wizard.storage.data["step_data"][STEP_HARVEST_SHARES].items():
            if key.startswith("Harvest Shares-harvest_shares_") and int(val[0]) > 0:
                return True
        return False


@transaction.atomic
def save_member(form_dict):
    personal_details_form = form_dict[STEP_PERSONAL_DETAILS]
    member = personal_details_form.forms[0].instance

    member.account_owner = personal_details_form.cleaned_data["account_owner"]
    member.iban = personal_details_form.cleaned_data["iban"]
    member.is_active = False

    now = get_now()
    member.sepa_consent = now
    member.withdrawal_consent = now
    member.privacy_consent = now

    member.save()

    return member


@method_decorator(xframe_options_exempt, name="dispatch")
@method_decorator(xframe_options_exempt, name="post")
class RegistrationWizardView(CookieWizardView):
    template_name = "wirgarten/registration/registration_wizard.html"
    finish_button_label = _("Bestellung abschließen")

    form_list = [
        (STEP_HARVEST_SHARES, HarvestShareForm),
        (STEP_NO_HARVEST_SHARES_AVAILABLE, EmptyForm),
        (STEP_COOP_SHARES, CooperativeShareForm),
        (STEP_NO_COOP_SHARES_AVAILABLE, EmptyForm),
        (STEP_ADDITIONAL_SHARES, ChickenShareForm),
        (STEP_BESTELLCOOP, BestellCoopForm),
        (STEP_PICKUP_LOCATION, PickupLocationChoiceForm),
        (STEP_SUMMARY, SummaryForm),
        (STEP_PERSONAL_DETAILS, PersonalDataRegistrationForm),
    ]

    def __init__(self, *args, **kwargs):
        super(RegistrationWizardView, self).__init__(*args, **kwargs)

        today = get_today()
        reference_date = max(today, date(2023, 6, 15))
        self.growing_period = GrowingPeriod.objects.filter(
            start_date__lte=reference_date + relativedelta(months=1, day=1),
            end_date__gte=reference_date + relativedelta(months=1, day=1),
        ).first()

        self.start_date = get_next_contract_start_date(max(today, reference_date))
        self.end_date = self.growing_period.end_date

    def dispatch(self, request, *args, **kwargs):
        self.coop_shares_only = (
            "coop_shares_only" in request.GET
            and request.GET["coop_shares_only"] == "true"
        )
        self.condition_dict = self.init_conditions()
        return super().dispatch(request, *args, **kwargs)

    def init_conditions(self):
        try:
            _show_harvest_shares = is_harvest_shares_available(
                reference_date=self.start_date
            )
            _coop_shares_without_harvest_shares_possible = get_parameter_value(
                Parameter.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES
            )
            _chicken_shares_available = is_chicken_shares_available(
                reference_date=self.start_date
            )
            _bestellcoop_available = is_bestellcoop_available(
                reference_date=self.start_date
            )

            return {
                STEP_HARVEST_SHARES: self.coop_shares_only == False
                and _show_harvest_shares,
                STEP_NO_HARVEST_SHARES_AVAILABLE: self.coop_shares_only == False
                and not _show_harvest_shares,
                STEP_COOP_SHARES: (lambda x: has_selected_harvest_shares(x))
                if not _coop_shares_without_harvest_shares_possible
                else True,
                STEP_NO_COOP_SHARES_AVAILABLE: (
                    (lambda x: not has_selected_harvest_shares(x))
                    if not _coop_shares_without_harvest_shares_possible
                    else False
                ),
                STEP_ADDITIONAL_SHARES: has_selected_harvest_shares
                if _chicken_shares_available
                else False,
                STEP_BESTELLCOOP: has_selected_harvest_shares
                if _bestellcoop_available
                else False,
                STEP_PICKUP_LOCATION: has_selected_harvest_shares,
                STEP_SUMMARY: self.coop_shares_only == False,
            }
        except Exception as e:
            print("Could not init registration wizard conditions: ", e)

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
        if step in [STEP_HARVEST_SHARES, STEP_ADDITIONAL_SHARES, STEP_BESTELLCOOP]:
            initial["start_date"] = self.start_date

        if step == STEP_COOP_SHARES:
            if self.has_step(STEP_HARVEST_SHARES):
                data = self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
                for key, val in data.items():
                    initial[key] = val
        elif step == STEP_PICKUP_LOCATION:
            # TODO: has to be implemented with product_type.id not name when the wizard generically handles all products
            initial["subs"] = {}
            if self.has_step(STEP_HARVEST_SHARES) and is_harvest_shares_selected(
                self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
            ):
                initial["subs"][ProductTypes.HARVEST_SHARES] = []
                data = self.get_cleaned_data_for_step(STEP_HARVEST_SHARES)
                for key, quantity in data.items():
                    if key.startswith("harvest_shares_"):
                        product_name = key.replace("harvest_shares_", "")
                        product = Product.objects.get(
                            name__iexact=product_name,
                            type__name=ProductTypes.HARVEST_SHARES,
                        )
                        initial["subs"][ProductTypes.HARVEST_SHARES].append(
                            Subscription(product=product, quantity=quantity)
                        )

            if self.has_step(STEP_ADDITIONAL_SHARES) and is_chicken_shares_selected(
                self.get_cleaned_data_for_step(STEP_ADDITIONAL_SHARES)
            ):
                initial["subs"][ProductTypes.CHICKEN_SHARES] = []
                data = self.get_cleaned_data_for_step(STEP_ADDITIONAL_SHARES)
                for key, quantity in data.items():
                    if key.startswith("chicken_shares_"):
                        product_name = key.replace("chicken_shares_", "")
                        product = Product.objects.get(
                            name__iexact=product_name,
                            type__name=ProductTypes.CHICKEN_SHARES,
                        )
                        initial["subs"][ProductTypes.CHICKEN_SHARES].append(
                            Subscription(product=product, quantity=quantity)
                        )
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

        if STEP_PICKUP_LOCATION in form_dict:
            MemberPickupLocation.objects.create(
                member=member,
                pickup_location_id=form_dict[STEP_PICKUP_LOCATION]
                .cleaned_data["pickup_location"]
                .id,
                valid_from=get_today(),
            )

        # coop membership starts after the cancellation period, so I call get_next_start_date() to add 1 month
        actual_coop_start = get_next_contract_start_date(self.start_date)
        buy_cooperative_shares(
            quantity=form_dict[STEP_COOP_SHARES].cleaned_data["cooperative_shares"]
            / settings.COOP_SHARE_PRICE,
            member=member,
            start_date=actual_coop_start,
        )

        if STEP_HARVEST_SHARES in form_dict and is_harvest_shares_selected(
            form_dict[STEP_HARVEST_SHARES].cleaned_data
        ):
            mandate_ref = create_mandate_ref(member)
            form_dict[STEP_HARVEST_SHARES].save(
                mandate_ref=mandate_ref,
                member_id=member.id,
            )

            if self.has_step(STEP_ADDITIONAL_SHARES):
                form_dict[STEP_ADDITIONAL_SHARES].save(
                    member_id=member.id,
                    mandate_ref=mandate_ref,
                )
            if self.has_step(STEP_BESTELLCOOP):
                form_dict[STEP_BESTELLCOOP].save(
                    member_id=member.id,
                    mandate_ref=mandate_ref,
                )

            send_order_confirmation(
                member, get_future_subscriptions().filter(member=member)
            )

        return HttpResponseRedirect(
            reverse_lazy("wirgarten:draftuser_confirm_registration")
            + "?member="
            + member.id
        )


@method_decorator(xframe_options_exempt, name="dispatch")
class RegistrationWizardConfirmView(generic.TemplateView):
    template_name = "wirgarten/registration/confirmation.html"


def questionaire_trafficsource_view(request, **kwargs):
    if request.method == "POST":
        form = MarketingFeedbackForm(request.POST)
        if form.is_valid():
            member_id = request.environ["QUERY_STRING"].replace("member=", "")
            form.save(member_id=member_id)
    else:
        form = MarketingFeedbackForm()

    context = {
        "form": form,
    }
    return render(request, "wirgarten/registration/user_response.html", context)


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
