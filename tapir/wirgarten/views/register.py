from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.clickjacking import xframe_options_exempt
from formtools.wizard.views import CookieWizardView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.forms.empty_form import EmptyForm
from tapir.wirgarten.forms.member import (
    MarketingFeedbackForm,
    PersonalDataRegistrationForm,
)
from tapir.wirgarten.forms.pickup_location import PickupLocationChoiceForm
from tapir.wirgarten.forms.registration.coop_shares import CooperativeShareForm
from tapir.wirgarten.forms.subscription import (
    BASE_PRODUCT_FIELD_PREFIX,
    AdditionalProductForm,
    BaseProductForm,
)
from tapir.wirgarten.models import (
    MemberPickupLocation,
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import (
    buy_cooperative_shares,
    create_mandate_ref,
    get_next_contract_start_date,
)
from tapir.wirgarten.service.products import (
    get_available_product_types,
    get_current_growing_period,
    is_product_type_available,
)
from tapir.wirgarten.utils import get_now, get_today


def questionaire_trafficsource_view(request, **_):
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


# 1. Harvest Shares, if not available, skip to 1.5
# 1.5. No Harvest Shares Available
# 2. Cooperative Shares, if not available, skip to 2.5
# 2.5. No Cooperative Shares Available
# 3-n. Additional Shares
# n+1. Pickup Location
# n+2. Summary
# n+3. Personal Details

STEP_BASE_PRODUCT = "base_product"
STEP_BASE_PRODUCT_NOT_AVAILABLE = "base_product_not_available"
STEP_COOP_SHARES = "coop_shares"
STEP_COOP_SHARES_NOT_AVAILABLE = "coop_shares_not_available"
STEP_PICKUP_LOCATION = "pickup_location"
STEP_SUMMARY = "summary"
STEP_PERSONAL_DETAILS = "personal_details"

STATIC_STEPS = [
    STEP_BASE_PRODUCT,
    STEP_BASE_PRODUCT_NOT_AVAILABLE,
    STEP_COOP_SHARES,
    STEP_COOP_SHARES_NOT_AVAILABLE,
    STEP_PICKUP_LOCATION,
    STEP_SUMMARY,
    STEP_PERSONAL_DETAILS,
]


@method_decorator(xframe_options_exempt, name="dispatch")
@method_decorator(xframe_options_exempt, name="post")
class RegistrationWizardViewBase(CookieWizardView):
    template_name = "wirgarten/registration/registration_wizard.html"
    finish_button_label = _("Bestellung abschließen")
    additional_steps_kwargs = {}

    def __init__(self, *args, **kwargs):
        super(RegistrationWizardViewBase, self).__init__(*args, **kwargs)

        today = get_today()
        self.growing_period = get_current_growing_period(
            get_next_contract_start_date(today)
        )

        if not self.growing_period:
            self.coop_shares_only = True
        else:
            self.start_date = get_next_contract_start_date(today)
            self.end_date = self.growing_period.end_date

        self.dynamic_steps = [f for f in self.form_list if f not in STATIC_STEPS]

    @classmethod
    def get_summary_form(cls):
        raise not NotImplementedError(
            "Please implement get_summary_form in the inherited class()"
        )

    @classmethod
    def as_view(cls, *args, **kwargs):
        base_prod_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        form_list = [
            (STEP_BASE_PRODUCT, BaseProductForm),
            (STEP_BASE_PRODUCT_NOT_AVAILABLE, EmptyForm),
            (STEP_COOP_SHARES, CooperativeShareForm),
            (STEP_COOP_SHARES_NOT_AVAILABLE, EmptyForm),
        ]
        steps_kwargs = settings.REGISTRATION_STEPS
        if STEP_BASE_PRODUCT not in steps_kwargs:
            base_product = ProductType.objects.get(id=base_prod_id)
            steps_kwargs[STEP_BASE_PRODUCT] = {
                "product_type_id": base_prod_id,
                "title": base_product.name,
                "description": base_product.name,
            }
        steps_kwargs[STEP_BASE_PRODUCT]["product_type_id"] = base_prod_id
        for pt in [
            x
            for x in get_available_product_types(get_next_contract_start_date())
            if x.id != base_prod_id
        ]:
            step = "additional_product_" + pt.name
            if step not in steps_kwargs:
                steps_kwargs[step] = {
                    "product_type_id": pt.id,
                    "title": pt.name,
                    "description": pt.name,
                }

            steps_kwargs[step]["product_type_id"] = pt.id
            form_list.append(
                (
                    step,
                    AdditionalProductForm,
                )
            )

        form_list.extend(
            [
                (STEP_PICKUP_LOCATION, PickupLocationChoiceForm),
                (STEP_SUMMARY, cls.get_summary_form()),
                (STEP_PERSONAL_DETAILS, PersonalDataRegistrationForm),
            ]
        )

        return super().as_view(
            *args,
            **kwargs,
            form_list=form_list,
            additional_steps_kwargs=steps_kwargs,
        )

    def dispatch(self, request, *args, **kwargs):
        """
        This method is called when the request is first received. If '?coop_shares_only=true' is set in the request,
        the wizard will skip the harvest shares step and only show the coop shares step and skips the summary as well.
        """
        self.coop_shares_only = (
            hasattr(self, "coop_shares_only") and self.coop_shares_only
        ) or ("coop_shares_only" in request.GET)

        self.condition_dict = self.init_conditions()
        return super().dispatch(request, *args, **kwargs)

    def init_conditions(self):
        if self.coop_shares_only:
            return {
                STEP_BASE_PRODUCT: False,
                STEP_BASE_PRODUCT_NOT_AVAILABLE: False,
                STEP_COOP_SHARES: True,
                STEP_COOP_SHARES_NOT_AVAILABLE: False,
                STEP_PICKUP_LOCATION: False,
                STEP_SUMMARY: False,
                **{f: False for f in self.dynamic_steps},
            }

        _coop_shares_without_harvest_shares_possible = get_parameter_value(
            Parameter.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES
        )

        _show_harvest_shares = is_product_type_available(
            ProductType.objects.get(
                id=get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
            ),
            reference_date=self.start_date,
        )

        return {
            STEP_BASE_PRODUCT: _show_harvest_shares,
            STEP_BASE_PRODUCT_NOT_AVAILABLE: self.coop_shares_only == False
            and not _show_harvest_shares,
            STEP_COOP_SHARES: (lambda x: has_selected_base_product(x))
            if not _coop_shares_without_harvest_shares_possible
            else True,
            STEP_COOP_SHARES_NOT_AVAILABLE: (
                (lambda x: not has_selected_base_product(x))
                if not _coop_shares_without_harvest_shares_possible
                else False
            ),
            **{f: lambda x: has_selected_base_product(x) for f in self.dynamic_steps},
            STEP_PICKUP_LOCATION: lambda x: has_selected_base_product(x),
            STEP_SUMMARY: lambda x: has_selected_base_product(x)
            if self.coop_shares_only == False
            else True,
        }

    def has_step(self, step):
        return step in self.storage.data["step_data"]

    def get_template_names(self):
        if self.steps.current == STEP_BASE_PRODUCT_NOT_AVAILABLE:
            return ["registration/steps/harvest_shares_no_subscription.html"]
        elif self.steps.current == STEP_COOP_SHARES_NOT_AVAILABLE:
            return ["registration/steps/coop_shares_not_available.html"]
        elif self.steps.current == STEP_SUMMARY:
            return ["registration/steps/summary.html"]
        return ["wirgarten/registration/registration_form.html"]

    # gather data from dependent forms
    def get_form_initial(self, step=None):
        initial = self.initial_dict
        if step in [STEP_BASE_PRODUCT, *self.dynamic_steps]:
            initial["start_date"] = self.start_date
            initial = {**initial, **self.additional_steps_kwargs[step]}
        if step == STEP_COOP_SHARES:
            initial = {**initial, **self.additional_steps_kwargs[step]}
            if self.has_step(STEP_BASE_PRODUCT):
                data = self.get_cleaned_data_for_step(STEP_BASE_PRODUCT)
                for key, val in data.items():
                    initial[key] = val
        elif step in self.dynamic_steps:
            initial = self.initial_dict
            initial = {**initial, **self.additional_steps_kwargs[step]}
        elif step == STEP_PICKUP_LOCATION:
            initial["subs"] = {}
            if self.has_step(STEP_BASE_PRODUCT) and is_base_product_selected(
                self.get_cleaned_data_for_step(STEP_BASE_PRODUCT)
            ):
                base_product_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
                product_type = ProductType.objects.get(id=base_product_id)
                initial["subs"][product_type.name] = []
                data = self.get_cleaned_data_for_step(STEP_BASE_PRODUCT)
                for key, quantity in data.items():
                    if key.startswith(BASE_PRODUCT_FIELD_PREFIX):
                        product_name = key.replace(BASE_PRODUCT_FIELD_PREFIX, "")
                        product = Product.objects.get(
                            name__iexact=product_name,
                            type_id=get_parameter_value(
                                Parameter.COOP_BASE_PRODUCT_TYPE
                            ),
                        )
                        initial["subs"][product_type.name].append(
                            Subscription(product=product, quantity=quantity)
                        )
                for dyn_step in self.dynamic_steps:
                    if self.has_step(dyn_step):
                        product_type = ProductType.objects.get(
                            id=self.additional_steps_kwargs[dyn_step]["product_type_id"]
                        )
                        initial["subs"][product_type.name] = []
                        data = self.get_cleaned_data_for_step(dyn_step)
                        for key, quantity in data.items():
                            if key.startswith(product_type.id + "_"):
                                product_name = key.replace(product_type.id + "_", "")
                                product = Product.objects.get(
                                    name__iexact=product_name,
                                    type_id=product_type.id,
                                )
                                initial["subs"][product_type.name].append(
                                    Subscription(product=product, quantity=quantity)
                                )
        elif step == STEP_SUMMARY:
            initial["general"] = {
                "start_date": self.start_date,
                "end_date": self.end_date,
            }
            if self.has_step(STEP_BASE_PRODUCT):
                base_prod_data = self.get_cleaned_data_for_step(STEP_BASE_PRODUCT)
                initial[STEP_BASE_PRODUCT] = base_prod_data

                if is_base_product_selected(base_prod_data):
                    for dyn_step in self.dynamic_steps:
                        if "additional_shares" not in initial:
                            initial["additional_shares"] = {}
                        if self.has_step(dyn_step):
                            initial["additional_shares"][
                                dyn_step
                            ] = self.get_cleaned_data_for_step(dyn_step)
                    initial["pickup_location"] = self.get_cleaned_data_for_step(
                        STEP_PICKUP_LOCATION
                    )
            else:
                initial[STEP_BASE_PRODUCT] = {}

            initial["coop_shares"] = (
                self.get_cleaned_data_for_step(STEP_COOP_SHARES)
                if self.has_step(STEP_COOP_SHARES)
                else {"cooperative_shares": 0}
            )

        return initial

    @transaction.atomic
    def save_member(self, form_dict):
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

    @transaction.atomic
    def done(self, form_list, form_dict, **kwargs):
        member = self.save_member(form_dict)

        try:
            if STEP_PICKUP_LOCATION in form_dict:
                MemberPickupLocation.objects.create(
                    member=member,
                    pickup_location_id=form_dict[STEP_PICKUP_LOCATION]
                    .cleaned_data["pickup_location"]
                    .id,
                    valid_from=get_today(),
                )

            start_date = (
                self.start_date
                if hasattr(self, "start_date")
                else get_next_contract_start_date()
            )
            self.growing_period = form_dict[STEP_BASE_PRODUCT].cleaned_data.get(
                "growing_period", get_current_growing_period()
            )
            if self.growing_period and self.growing_period.start_date > get_today():
                start_date = self.growing_period.start_date
            # coop membership starts after the cancellation period, so I call get_next_start_date() to add 1 month
            actual_coop_start = get_next_contract_start_date(ref_date=start_date)

            mandate_ref = create_mandate_ref(member)
            buy_cooperative_shares(
                quantity=form_dict[STEP_COOP_SHARES].cleaned_data["cooperative_shares"]
                / settings.COOP_SHARE_PRICE,
                member=member,
                start_date=actual_coop_start,
                mandate_ref=mandate_ref,
            )

            if STEP_BASE_PRODUCT in form_dict and is_base_product_selected(
                form_dict[STEP_BASE_PRODUCT].cleaned_data
            ):
                form_dict[STEP_BASE_PRODUCT].save(
                    mandate_ref=mandate_ref,
                    member_id=member.id,
                )

                for dyn_step in self.dynamic_steps:
                    if self.has_step(dyn_step):
                        form_dict[dyn_step].save(
                            mandate_ref=mandate_ref,
                            member_id=member.id,
                        )
        except Exception as e:
            member.delete()
            raise e

        return HttpResponseRedirect(
            reverse_lazy("wirgarten:draftuser_confirm_registration")
            + "?member="
            + member.id
        )


@method_decorator(xframe_options_exempt, name="dispatch")
class RegistrationWizardConfirmView(generic.TemplateView):
    template_name = "registration/confirmation.html"


def is_selected(form_data, prefix):
    for key, val in form_data.items():
        if key.startswith(prefix) and (val or 0) > 0:
            return True
    return False


def is_base_product_selected(harvest_share_form_data):
    return is_selected(harvest_share_form_data, BASE_PRODUCT_FIELD_PREFIX)


def has_selected_base_product(wizard) -> bool:
    if (
        "step_data" in wizard.storage.data
        and STEP_BASE_PRODUCT in wizard.storage.data["step_data"]
    ):
        for key, val in wizard.storage.data["step_data"][STEP_BASE_PRODUCT].items():
            if (
                key.startswith(f"{STEP_BASE_PRODUCT}-{BASE_PRODUCT_FIELD_PREFIX}")
                and int(val[0] or 0) > 0
            ):
                return True
    return False
