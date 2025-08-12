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
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.core.config import LEGAL_STATUS_COOPERATIVE, THEME_L2G
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.constants import NO_DELIVERY
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
    Member,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    create_mandate_ref,
    send_order_confirmation,
)
from tapir.wirgarten.service.products import (
    get_available_product_types,
    get_active_and_future_subscriptions,
    is_product_type_available,
)
from tapir.wirgarten.utils import get_now, get_today, legal_status_is_cooperative


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

        self.cache = {}

        today = get_today(cache=self.cache)
        next_contract_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=today, apply_buffer_time=True, cache=self.cache
            )
        )

        self.growing_period = TapirCache.get_growing_period_at_date(
            reference_date=next_contract_start_date,
            cache=self.cache,
        )
        self.start_date = next_contract_start_date
        self.end_date = self.growing_period.end_date if self.growing_period else None

        self.dynamic_steps = [f for f in self.form_list if f not in STATIC_STEPS]

    @classmethod
    def get_summary_form(cls):
        raise NotImplementedError(
            "Please implement get_summary_form in the inherited class()"
        )

    @classmethod
    def as_view(cls, *args, **kwargs):
        cache = {}
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)
        form_list = [
            (STEP_BASE_PRODUCT, BaseProductForm),
            (STEP_BASE_PRODUCT_NOT_AVAILABLE, EmptyForm),
        ]
        if (
            get_parameter_value(ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=cache)
            == LEGAL_STATUS_COOPERATIVE
        ):
            form_list += [
                (STEP_COOP_SHARES, CooperativeShareForm),
                (STEP_COOP_SHARES_NOT_AVAILABLE, EmptyForm),
            ]

        steps_kwargs = settings.REGISTRATION_STEPS
        for steps_kwargs_key in steps_kwargs.keys():
            wip_kwargs = steps_kwargs[steps_kwargs_key]
            if "intro_template" in wip_kwargs.keys():
                base_template_path = wip_kwargs["intro_template"]
                theme_template = base_template_path.replace(
                    "steps/",
                    f"steps/{get_parameter_value(ParameterKeys.ORGANISATION_THEME)}/",
                )
                wip_kwargs["intro_templates"] = [theme_template, base_template_path]

            if "outro_template" in wip_kwargs.keys():
                base_template_path = wip_kwargs["outro_template"]
                theme_template = base_template_path.replace(
                    "steps/",
                    f"steps/{get_parameter_value(ParameterKeys.ORGANISATION_THEME)}/",
                )
                wip_kwargs["outro_templates"] = [theme_template, base_template_path]

            steps_kwargs[steps_kwargs_key] = wip_kwargs

        if STEP_BASE_PRODUCT not in steps_kwargs:
            steps_kwargs[STEP_BASE_PRODUCT] = {
                "product_type_id": base_product_type.id,
                "title": base_product_type.name,
                "description": base_product_type.name,
            }
        steps_kwargs[STEP_BASE_PRODUCT]["product_type_id"] = (
            base_product_type.id if base_product_type is not None else None
        )
        next_contract_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=cache),
                apply_buffer_time=True,
                cache=cache,
            )
        )
        available_and_additional_product_types = [
            product_type
            for product_type in get_available_product_types(
                next_contract_start_date, cache=cache
            )
            if product_type.id != base_product_type.id
        ]

        for pt in available_and_additional_product_types:
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

        if (
            get_parameter_value(ParameterKeys.ORGANISATION_THEME, cache=cache)
            == THEME_L2G
        ):
            steps_kwargs["pickup_location"][
                "description"
            ] = "Abholort – Hier wird dein Anteil bereitgestellt"
        else:
            steps_kwargs["pickup_location"][
                "description"
            ] = "Abholort - Wo möchtest du dein Gemüse abholen?"

        return super().as_view(
            *args,
            **kwargs,
            form_list=form_list,
            additional_steps_kwargs=steps_kwargs,
        )

    def dispatch(self, request, *args, **kwargs):
        self.condition_dict = self.init_conditions()
        return super().dispatch(request, *args, **kwargs)

    def init_conditions(self):
        _coop_shares_without_harvest_shares_possible = get_parameter_value(
            ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES, cache=self.cache
        )

        _show_harvest_shares = is_product_type_available(
            BaseProductTypeService.get_base_product_type(cache=self.cache),
            reference_date=self.start_date,
            cache=self.cache,
        )

        if legal_status_is_cooperative(cache=self.cache):
            step_coop_shares_enabled = True
            step_coop_shares_enabled_not_available_enabled = False
            if not _coop_shares_without_harvest_shares_possible:
                step_coop_shares_enabled = lambda x: has_selected_base_product(x)
                step_coop_shares_enabled_not_available_enabled = (
                    lambda x: not has_selected_base_product(x)
                )

        else:
            step_coop_shares_enabled = False
            step_coop_shares_enabled_not_available_enabled = False

        if get_parameter_value(
            ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            cache=self.cache,
        ):
            show_additional_products = True
        else:
            show_additional_products = lambda wizard: has_selected_base_product(wizard)

        return {
            STEP_BASE_PRODUCT: _show_harvest_shares,
            STEP_BASE_PRODUCT_NOT_AVAILABLE: not _show_harvest_shares,
            STEP_COOP_SHARES: step_coop_shares_enabled,
            STEP_COOP_SHARES_NOT_AVAILABLE: step_coop_shares_enabled_not_available_enabled,
            **{
                additional_product_step: show_additional_products
                for additional_product_step in self.dynamic_steps
            },
            STEP_PICKUP_LOCATION: lambda x: has_selected_at_least_one_deliverable_product(
                x
            ),
            STEP_SUMMARY: True,
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
        cache = {}
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
                base_product_type_id = BaseProductTypeService.get_base_product_type(
                    cache=cache
                ).id
                product_type = ProductType.objects.get(id=base_product_type_id)
                initial["subs"][product_type.name] = []
                data = self.get_cleaned_data_for_step(STEP_BASE_PRODUCT)
                for key, quantity in data.items():
                    if key.startswith(BASE_PRODUCT_FIELD_PREFIX):
                        product_name = key.replace(BASE_PRODUCT_FIELD_PREFIX, "")
                        product = Product.objects.get(
                            name__iexact=product_name,
                            type_id=base_product_type_id,
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

                if is_base_product_selected(base_prod_data) or get_parameter_value(
                    ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
                    cache=cache,
                ):
                    for dyn_step in self.dynamic_steps:
                        if "additional_shares" not in initial:
                            initial["additional_shares"] = {}
                        if self.has_step(dyn_step):
                            initial["additional_shares"][dyn_step] = (
                                self.get_cleaned_data_for_step(dyn_step)
                            )
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
        member: Member = personal_details_form.forms[0].instance

        member.account_owner = personal_details_form.cleaned_data["account_owner"]
        member.iban = personal_details_form.cleaned_data["iban"]
        member.is_active = False

        if STEP_COOP_SHARES in form_dict.keys():
            member.is_student = form_dict[STEP_COOP_SHARES].cleaned_data["is_student"]

        now = get_now()
        member.sepa_consent = now
        member.withdrawal_consent = now
        member.privacy_consent = now

        member.save()

        return member

    @transaction.atomic
    def done(self, form_list, form_dict, **kwargs):
        today = get_today(cache=self.cache)
        member = self.save_member(form_dict)
        try:
            if STEP_PICKUP_LOCATION in form_dict:
                MemberPickupLocation.objects.create(
                    member=member,
                    pickup_location_id=form_dict[STEP_PICKUP_LOCATION]
                    .cleaned_data["pickup_location"]
                    .id,
                    valid_from=today,
                )

            start_date = (
                self.start_date
                if hasattr(self, "start_date")
                else ContractStartDateCalculator.get_next_contract_start_date(
                    reference_date=today, apply_buffer_time=True, cache=self.cache
                )
            )
            if STEP_BASE_PRODUCT in form_dict:
                self.growing_period = form_dict[STEP_BASE_PRODUCT].cleaned_data.get(
                    "growing_period",
                    TapirCache.get_growing_period_at_date(
                        reference_date=today, cache=self.cache
                    ),
                )
            if self.growing_period and self.growing_period.start_date > today:
                start_date = self.growing_period.start_date
            # coop membership starts after the cancellation period, so I call get_next_start_date() to add 1 month
            actual_coop_start = get_first_of_next_month(date=start_date)

            mandate_ref = create_mandate_ref(member, cache=self.cache)
            if not member.is_student and STEP_COOP_SHARES in form_dict.keys():
                number_of_shares = (
                    form_dict[STEP_COOP_SHARES].cleaned_data["cooperative_shares"]
                    / settings.COOP_SHARE_PRICE
                )
                CoopSharePurchaseHandler.buy_cooperative_shares(
                    quantity=number_of_shares,
                    member=member,
                    shares_valid_at=actual_coop_start,
                    cache=self.cache,
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

                send_order_confirmation(
                    member,
                    get_active_and_future_subscriptions().filter(member=member),
                    cache=self.cache,
                    from_waiting_list=False,
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

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["coop_info_link"] = get_parameter_value(
            ParameterKeys.COOP_INFO_LINK
        )
        return context_data


def is_selected(form_data, prefix):
    for key, val in form_data.items():
        if key.startswith(prefix) and (val or 0) > 0:
            return True
    return False


def is_base_product_selected(harvest_share_form_data):
    return is_selected(harvest_share_form_data, BASE_PRODUCT_FIELD_PREFIX)


def has_selected_base_product(wizard) -> bool:
    if (
        "step_data" not in wizard.storage.data
        or STEP_BASE_PRODUCT not in wizard.storage.data["step_data"]
    ):
        return False

    for key, val in wizard.storage.data["step_data"][STEP_BASE_PRODUCT].items():
        if (
            key.startswith(f"{STEP_BASE_PRODUCT}-{BASE_PRODUCT_FIELD_PREFIX}")
            and int(val[0] or 0) > 0
        ):
            return True

    return False


def has_selected_at_least_one_deliverable_product(wizard) -> bool:
    for key, val in (
        wizard.storage.data.get("step_data", {}).get(STEP_BASE_PRODUCT, {}).items()
    ):
        if (
            key.startswith(f"{STEP_BASE_PRODUCT}-{BASE_PRODUCT_FIELD_PREFIX}")
            and int(val[0] or 0) > 0
        ):
            return True

    for product_type in ProductType.objects.exclude(delivery_cycle=NO_DELIVERY[0]):
        step = "additional_product_" + product_type.name
        for key, val in wizard.storage.data.get("step_data", {}).get(step, {}).items():
            if key.startswith(f"{step}-") and int(val[0] or 0) > 0:
                return True

    return False
