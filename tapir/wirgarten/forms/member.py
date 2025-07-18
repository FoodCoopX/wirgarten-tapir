from datetime import datetime

from bootstrap_datepicker_plus.widgets import DatePickerInput
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import transaction
from django.db.models import F, Sum, Q
from django.forms import (
    BooleanField,
    CharField,
    CheckboxInput,
    CheckboxSelectMultiple,
    ChoiceField,
    DateField,
    DecimalField,
    Form,
    IntegerField,
    ModelForm,
    ModelMultipleChoiceField,
    MultipleChoiceField,
)
from django.utils.translation import gettext_lazy as _

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_text_service import MembershipTextService
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.forms import TapirPhoneNumberField
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.form_mixins import FormWithRequestMixin
from tapir.wirgarten.forms.registration.consents import ConsentForm
from tapir.wirgarten.forms.registration.payment_data import PaymentDataForm
from tapir.wirgarten.forms.subscription import AdditionalProductForm, BaseProductForm
from tapir.wirgarten.models import (
    CoopShareTransaction,
    Member,
    Payment,
    QuestionaireTrafficSourceOption,
    QuestionaireTrafficSourceResponse,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    send_cancellation_confirmation_email,
    send_order_confirmation,
)
from tapir.wirgarten.service.products import (
    get_available_product_types,
    get_active_and_future_subscriptions,
    get_active_subscriptions,
)
from tapir.wirgarten.utils import format_date, get_today, get_now


class PersonalDataForm(FormWithRequestMixin, ModelForm):
    n_columns = 2

    def __init__(self, *args, **kwargs):
        can_edit_name_and_birthdate = kwargs.pop("can_edit_name_and_birthdate", True)
        can_edit_email = kwargs.pop("can_edit_email", True)

        super(PersonalDataForm, self).__init__(*args, **kwargs)
        for k, v in self.fields.items():
            if k not in ["street_2", "is_student"]:
                v.required = True

        self.fields["first_name"].disabled = not can_edit_name_and_birthdate
        self.fields["last_name"].disabled = not can_edit_name_and_birthdate
        self.fields["birthdate"].disabled = not can_edit_name_and_birthdate
        self.fields["email"].disabled = not can_edit_email
        self.fields["first_name"].label = _("Vorname")
        self.fields["last_name"].label = _("Nachname")
        self.fields["street"].label = _("Straße & Hausnummer")
        self.fields["street_2"].label = _("Adresszusatz")
        self.fields["postcode"].label = _("Postleitzahl")
        self.fields["city"].label = _("Stadt")
        self.fields["country"].label = _("Land")
        self.fields["birthdate"].label = _("Geburtsdatum")

        if self.request and not self.request.user.has_perm(Permission.Accounts.MANAGE):
            self.fields["is_student"].disabled = True

    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "street",
            "street_2",
            "postcode",
            "city",
            "country",
            "birthdate",
            "is_student",
        ]
        widgets = {"birthdate": DatePickerInput(options={"format": "DD.MM.YYYY"})}

    phone_number = TapirPhoneNumberField(label=_("Telefon-Nr"))

    def clean_email(self):
        if "email" not in self.cleaned_data.keys():
            return None
        return self.cleaned_data["email"].strip().lower()

    def _validate_duplicate_email_keycloak(self):
        try:
            kc = KeycloakUserManager.get_keycloak_client()
            keycloak_id = kc.get_user_id(self.cleaned_data["email"])
            if keycloak_id is not None:
                raise ValidationError(
                    {
                        "email": _(
                            "Ein Nutzer mit dieser Email Adresse existiert bereits."
                        )
                    }
                )
        except Exception as e:
            pass

    def _validate_duplicate_email(self):
        email = self.cleaned_data["email"]

        duplicate_email_query = Member.objects.filter(
            Q(email=email) | Q(username=email)
        )
        if self.instance and self.instance.id:
            duplicate_email_query = duplicate_email_query.exclude(id=self.instance.id)

        if duplicate_email_query.exists():
            raise ValidationError(
                {"email": _("Ein Nutzer mit dieser Email Adresse existiert bereits.")}
            )

        original = Member.objects.filter(id=self.instance.id)
        if not original.exists():
            return

        original = original.first()
        email_changed = original.email != self.cleaned_data["email"]
        if email_changed:
            self._validate_duplicate_email_keycloak()

    def _validate_birthdate(self):
        birthdate = self.cleaned_data["birthdate"]
        today = get_today()
        if birthdate > today or birthdate < (today + relativedelta(years=-120)):
            self.add_error("birthdate", _("Bitte wähle ein gültiges Datum aus."))
        elif birthdate > (today + relativedelta(years=-18)):
            self.add_error(
                "birthdate",
                _(
                    "Du musst mindestens 18 Jahre alt sein um der Genossenschaft beizutreten."
                ),
            )

    def clean(self):
        self._validate_duplicate_email()
        self._validate_birthdate()


class MarketingFeedbackForm(Form):
    sources = ModelMultipleChoiceField(
        queryset=QuestionaireTrafficSourceOption.objects.all(),
        widget=CheckboxSelectMultiple,
        label="",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        sources = get_parameter_value(ParameterKeys.ORGANISATION_QUESTIONAIRE_SOURCES)
        sources = sources.split(",")
        sources = [source.strip() for source in sources]

        for source in sources:
            QuestionaireTrafficSourceOption.objects.get_or_create(name=source)

        queryset = self.fields["sources"].queryset
        self.fields["sources"].queryset = queryset.filter(name__in=sources)

    @transaction.atomic
    def save(self, **kwargs):
        sources = self.cleaned_data["sources"]
        if len(sources) > 0:
            member_id = kwargs.get("member_id", None)
            response = QuestionaireTrafficSourceResponse(
                member_id=member_id,
            )
            response.save()
            response.sources.set(sources)


class PersonalDataRegistrationForm(Form):
    n_columns = 2
    colspans = {
        "sepa_consent": 2,
        "withdrawal_consent": 2,
        "privacy_consent": 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        personal_data_form = PersonalDataForm(*args, **kwargs)
        personal_data_form.fields.pop("is_student")

        self.forms = [
            personal_data_form,
            PaymentDataForm(*args, **kwargs),
            ConsentForm(*args, **kwargs),
        ]

        for form in self.forms:
            for field_name, field in form.fields.items():
                self.fields[field_name] = field

    def is_valid(self):
        super().is_valid()
        for form in self.forms:
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == "__all__":
                            self.add_error(None, error)
                        else:
                            self.add_error(field, error)

        return len(self.errors) == 0


class PaymentAmountEditForm(Form):
    def __init__(self, *args, **kwargs):
        super(PaymentAmountEditForm, self).__init__(*args)

        self.initial_amount = kwargs.get("initial_amount", 0.0)
        self.mandate_ref_id = kwargs["mandate_ref_id"].replace("~", "/")
        self.payment_due_date = kwargs["payment_due_date"]
        self.payment_type = kwargs["payment_type"]

        payments = Payment.objects.filter(
            mandate_ref=self.mandate_ref_id,
            due_date=datetime.strptime(self.payment_due_date, "%d.%m.%Y").date(),
            type=self.payment_type,
        )

        if len(payments) < 1:
            initial = self.initial_amount
        elif len(payments) > 1:
            raise AssertionError("TOO MANY PAYMENTS FOUND!!")  # FIXME
        else:
            self.payment = payments[0]
            initial = self.payment.amount

        self.fields["comment"] = CharField(label=_("Änderungsgrund"), required=True)
        self.fields["amount"] = DecimalField(
            label=_("Neuer Betrag [€]"), initial=round(initial, 2)
        )
        self.fields["security_check"] = BooleanField(
            label=_(
                "Ich weiß was ich tue und bin mir der möglichen Konsequenzen bewusst."
            ),
            required=True,
            initial=False,
        )

    def is_valid(self):
        return (
            self.data["comment"]
            and self.data["security_check"]
            and float(self.data["amount"]) > 0
        )


class CoopShareTransferForm(Form):
    def __init__(self, *args, **kwargs):
        super(CoopShareTransferForm, self).__init__(*args)
        member_id = kwargs["pk"]
        orig_member = Member.objects.get(pk=member_id)
        self.orig_share_ownership_quantity = orig_member.coop_shares_quantity

        def member_to_string(m):
            return f"{m.first_name} {m.last_name} ({m.email})"

        choices = map(
            lambda x: (x.id, member_to_string(x)),
            Member.objects.exclude(pk=kwargs["pk"]).order_by(
                "first_name", "last_name", "email"
            ),
        )

        self.fields["origin"] = CharField(
            label=_("Ursprünglicher Anteilseigner")
            + f" ({self.orig_share_ownership_quantity if self.orig_share_ownership_quantity else 'KEINE'} Anteile)",
            disabled=True,
            initial=member_to_string(orig_member),
        )
        self.fields["receiver"] = ChoiceField(
            label=_("Empfänger der Genossenschaftsanteile"), choices=choices
        )
        self.fields["quantity"] = IntegerField(
            label=_("Anzahl der Anteile"),
            initial=self.orig_share_ownership_quantity,
            min_value=1,
            max_value=self.orig_share_ownership_quantity,
        )
        self.fields["security_check"] = BooleanField(
            label=_("Ich weiß was ich tue und bin mir der Konsequenzen bewusst."),
            required=True,
        )

    def is_valid(self):
        super().is_valid()
        remaining_shares = (
            self.orig_share_ownership_quantity - self.cleaned_data["quantity"]
        )
        min_shares = get_parameter_value(ParameterKeys.COOP_MIN_SHARES)
        if remaining_shares > 0 and remaining_shares < min_shares:
            self.add_error(
                "quantity",
                _(
                    "Ein Mitglied muss mindestens {min_shares} Genossenschaftsanteile haben."
                ).format(min_shares=min_shares),
            )
        return len(self.errors) == 0


class CoopShareCancelForm(Form):
    def __init__(self, *args, **kwargs):
        member_id = kwargs.pop("pk")
        super().__init__(*args, **kwargs)
        member = Member.objects.get(pk=member_id)
        self.original_share_quantity = member.coopsharetransaction_set.aggregate(
            quantity=Sum(F("quantity"))
        )["quantity"]
        today = get_today()
        valid_at = today + relativedelta(years=1, month=12, day=31)

        self.fields["cancellation_date"] = DateField(
            label=_("Kündigungsdatum"),
            initial=today,
            required=True,
            widget=DatePickerInput,
        )
        self.fields["valid_at"] = DateField(
            label=_("Kündigung gültig zum"),
            initial=valid_at,
            required=True,
            widget=DatePickerInput,
        )
        self.fields["quantity"] = IntegerField(
            label=_(
                "Anzahl der gekündigten Anteile (Insgesamt: {share_quantity})"
            ).format(share_quantity=self.original_share_quantity),
            initial=self.original_share_quantity,
            min_value=1,
            max_value=self.original_share_quantity,
        )
        self.fields["security_check"] = BooleanField(
            label=_("Ich weiß was ich tue und bin mir der Konsequenzen bewusst."),
            required=True,
        )

    def is_valid(self):
        super().is_valid()
        remaining_shares = self.original_share_quantity - self.cleaned_data["quantity"]
        min_shares = get_parameter_value(ParameterKeys.COOP_MIN_SHARES)
        if remaining_shares > 0 and remaining_shares < min_shares:
            self.add_error(
                "quantity",
                _(
                    "Ein Mitglied muss mindestens {min_shares} Genossenschaftsanteile haben."
                ).format(min_shares=min_shares),
            )
        return len(self.errors) == 0


class WaitingListForm(Form):
    n_columns = 2
    colspans = {"email": 2, "privacy_consent": 2}

    def __init__(self, *args, **kwargs):
        super(WaitingListForm, self).__init__(*args, **kwargs)
        self.fields["first_name"] = CharField(label=_("Vorname"))
        self.fields["last_name"] = CharField(label=_("Nachname"))
        self.fields["email"] = CharField(
            label=_("Email"), validators=[EmailValidator()]
        )
        self.fields["phone_number"] = TapirPhoneNumberField(label=_("Telefon-Nr"))
        self.fields["street"] = CharField(label=_("Adresse"))
        self.fields["street_2"] = CharField(label=_("Adresszusatz"))
        self.fields["postcode"] = CharField(label=_("Postleitzahl"))
        self.fields["city"] = CharField(label=_("Stadt"))
        self.fields["privacy_consent"] = BooleanField(
            label=_("Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen."),
            required=True,
            help_text=_(
                'Wir behandeln deine Daten vertraulich, verwenden diese nur im Rahmen der Mitgliederverwaltung und geben sie nicht an Dritte weiter. Unsere Datenschutzerklärung kannst du hier einsehen: <a target="_blank" href="{privacy_link}">Datenschutzerklärung - {site_name}</a>'
            ).format(
                site_name=get_parameter_value(ParameterKeys.SITE_NAME),
                privacy_link=get_parameter_value(ParameterKeys.SITE_PRIVACY_LINK),
            ),
        )


class TrialCancellationForm(Form):
    KEY_PREFIX = "sub_"
    BASE_PROD_TYPE_ATTR = "data-base-product-type"

    template_name = "wirgarten/member/trial_cancellation_form.html"

    def __init__(self, *args, **kwargs):
        self.cache = {}
        self.member_id = kwargs.pop("pk")
        super(TrialCancellationForm, self).__init__(*args, **kwargs)

        self.subs = TrialPeriodManager.get_subscriptions_in_trial_period(
            self.member_id, cache=self.cache
        )
        self.subs = Subscription.objects.filter(
            id__in=[subscription.id for subscription in self.subs]
        )
        trial_end_dates = [
            TrialPeriodManager.get_earliest_trial_cancellation_date(
                subscription, cache=self.cache
            )
            for subscription in self.subs
        ]
        self.next_trial_end_date = min(trial_end_dates, default=None)
        self.member = Member.objects.get(id=self.member_id)
        today = get_today(cache=self.cache)

        def is_new_member() -> bool:
            return (
                self.member.coop_entry_date is not None
                and self.member.coop_entry_date > today
            )

        base_product_type = BaseProductTypeService.get_base_product_type(
            cache=self.cache
        )
        for sub in self.subs:
            key = f"{self.KEY_PREFIX}{sub.id}"
            self.fields[key] = BooleanField(
                label=f"{sub.quantity} × {sub.product.name} {sub.product.type.name} ({format_date(sub.start_date)} - {format_date(sub.end_date)})",
                required=False,
            )
            if len(self.subs) > 1 and sub.product.type == base_product_type:
                self.fields[key].widget = CheckboxInput(
                    attrs={self.BASE_PROD_TYPE_ATTR: "true"}
                )

        if is_new_member():
            self.share_ownership = self.member.coopsharetransaction_set.filter(
                transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                valid_at__gt=self.next_trial_end_date,
            ).first()

            self.fields["cancel_coop"] = BooleanField(
                label=f"{MembershipTextService.get_membership_text(cache=self.cache)} widerrufen",
                required=False,
            )

    def is_valid(self):
        all_base_product_types_selected = True
        at_least_one_base_product_type_selected = False
        at_least_one_additional_product_type_selected = False
        for k, v in self.fields.items():
            if k in self.data:
                if self.BASE_PROD_TYPE_ATTR in v.widget.attrs:
                    at_least_one_base_product_type_selected = True
                    all_base_product_types_selected = False
                else:
                    at_least_one_additional_product_type_selected = True

        if (
            not at_least_one_base_product_type_selected
            and not at_least_one_additional_product_type_selected
        ):
            self.add_error(
                list(self.fields.keys())[0],
                _(
                    "Bitte wähle mindestens einen Vertrag aus, oder klick 'Abbrechen' falls du doch nicht kündigen möchtest."
                ),
            )
        elif (
            all_base_product_types_selected
            and not at_least_one_additional_product_type_selected
        ):
            self.add_error(
                list(self.fields.keys())[0],
                _("Du kannst keine Zusatzabos beziehen wenn du das Basisabo kündigst."),
            )

        return not self._errors and super(TrialCancellationForm, self).is_valid()

    def get_subs_to_cancel(self):
        return self.subs.filter(
            id__in=[
                key.replace("sub_", "")
                for key, value in self.cleaned_data.items()
                if value
            ]
        )

    def cancel_subscription(self, subscription: Subscription):
        subscription.cancellation_ts = get_now()
        subscription.end_date = self.next_trial_end_date
        subscription.save()

    @transaction.atomic
    def save(self, **_):
        cancel_coop = self.is_cancel_coop_selected()

        subs_to_cancel = self.get_subs_to_cancel()
        for sub in subs_to_cancel:
            self.cancel_subscription(sub)
        for cancelled_subscription in subs_to_cancel:
            # If the member first renewed during their trial period, but then cancels,
            # we also cancel the renewed contracts.
            is_any_subscription_of_same_type_still_active = (
                get_active_subscriptions()
                .filter(
                    member__id=self.member_id,
                    period=cancelled_subscription.period,
                    product__type=cancelled_subscription.product.type,
                    cancellation_ts=None,
                )
                .exists()
            )
            if not is_any_subscription_of_same_type_still_active:
                for future_subscription in get_active_and_future_subscriptions(
                    cache=self.cache
                ).filter(
                    member__id=self.member_id,
                    product__type=cancelled_subscription.product.type,
                    cancellation_ts=None,
                ):
                    self.cancel_subscription(future_subscription)

        if cancel_coop:
            if self.share_ownership.payment:
                self.share_ownership.payment.delete()
            self.share_ownership.delete()

        send_cancellation_confirmation_email(
            member=self.member_id,
            contract_end_date=self.next_trial_end_date,
            subs_to_cancel=subs_to_cancel,
            revoke_coop_membership=cancel_coop,
            cache=self.cache,
        )

        return (
            subs_to_cancel[0].end_date if subs_to_cancel else self.next_trial_end_date
        )

    def is_cancel_coop_selected(self):
        if not hasattr(self, "cancel_coop"):
            self.cancel_coop = (
                "cancel_coop" in self.cleaned_data
                and self.cleaned_data.pop("cancel_coop")
                and self.share_ownership
            )
        return self.cancel_coop


class SubscriptionRenewalForm(Form):
    template_name = "wirgarten/member/subscription_renewal_form.html"

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **{k: v for k, v in kwargs.items() if k not in ["start_date", "member_id"]},
        )
        self.start_date = kwargs["start_date"]
        self.cache = {}
        base_product_type = BaseProductTypeService.get_base_product_type(
            cache=self.cache
        )
        self.product_forms = [
            BaseProductForm(*args, **kwargs, enable_validation=True, cache=self.cache),
            *[
                AdditionalProductForm(
                    *args, **kwargs, product_type_id=product_type, cache=self.cache
                )
                for product_type in get_available_product_types(cache=self.cache)
                if product_type != base_product_type
            ],
        ]

        for form in self.product_forms:
            for field_name, field in form.fields.items():
                self.fields[field_name] = field

    def is_valid(self):
        super().is_valid()
        for form in self.product_forms:
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == "__all__":
                            self.add_error(None, error)
                        else:
                            self.add_error(field, error)

        return len(self.errors) == 0

    @transaction.atomic
    def save(self, *args, **kwargs):
        for form in self.product_forms:
            form.save(*args, **kwargs)

        TapirCache.clear_category(cache=self.cache, category="subscriptions")

        member_id = kwargs["member_id"]
        self.subs = get_active_and_future_subscriptions(
            self.start_date, cache=self.cache
        ).filter(member_id=member_id, cancellation_ts__isnull=True)

        member = Member.objects.get(id=member_id)
        send_order_confirmation(member, self.subs, cache=self.cache)


class CancellationReasonForm(Form):
    def __init__(self, *args, **kwargs):
        super(CancellationReasonForm, self).__init__(*args, **kwargs)
        self.fields["reason"] = MultipleChoiceField(
            label="Grund für deine Kündigung",
            choices=map(
                lambda x: (x.strip(), x.strip()),
                get_parameter_value(
                    ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES
                ).split(";"),
            ),
            widget=CheckboxSelectMultiple,
            required=False,
        )
        self.fields["custom_reason"] = CharField(
            label="Sonstiger Grund für deine Kündigung", required=False
        )
