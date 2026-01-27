from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import transaction
from django.db.models import F, Sum, Q
from django.forms import (
    BooleanField,
    CharField,
    CheckboxSelectMultiple,
    ChoiceField,
    DateField,
    DecimalField,
    Form,
    IntegerField,
    ModelForm,
    ModelMultipleChoiceField,
    MultipleChoiceField,
    DateInput,
)
from django.utils.translation import gettext_lazy as _

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.utils.forms import TapirPhoneNumberField
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.form_mixins import FormWithRequestMixin
from tapir.wirgarten.forms.registration.consents import ConsentForm
from tapir.wirgarten.forms.registration.payment_data import PaymentDataForm
from tapir.wirgarten.forms.subscription import AdditionalProductForm, BaseProductForm
from tapir.wirgarten.models import (
    Member,
    Payment,
    QuestionaireTrafficSourceOption,
    QuestionaireTrafficSourceResponse,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    send_product_order_confirmation,
)
from tapir.wirgarten.service.products import (
    get_available_product_types,
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import get_today


class PersonalDataForm(FormWithRequestMixin, ModelForm):
    n_columns = 2

    def __init__(self, *args, **kwargs):
        can_edit_name_and_birthdate = kwargs.pop("can_edit_name_and_birthdate", True)
        can_edit_email = kwargs.pop("can_edit_email", True)

        super(PersonalDataForm, self).__init__(*args, **kwargs)
        for k, v in self.fields.items():
            if k not in ["street_2", "is_student", "birthdate"]:
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
        widgets = {"birthdate": DateInput()}

    phone_number = TapirPhoneNumberField(label=_("Telefon-Nr"))

    def clean_email(self):
        if "email" not in self.cleaned_data.keys():
            return None
        return self.cleaned_data["email"].strip().lower()

    def _validate_duplicate_email_keycloak(self):
        try:
            kc = KeycloakUserManager.get_keycloak_client(cache={})
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
            self._validate_duplicate_email_keycloak()
            return

        original = original.first()
        email_changed = original.email != self.cleaned_data["email"]
        if email_changed:
            self._validate_duplicate_email_keycloak()

    def _validate_birthdate(self):
        birthdate = self.cleaned_data.get("birthdate", None)
        if birthdate is None:
            return
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

        TapirCacheManager.clear_category(cache=self.cache, category="subscriptions")

        member_id = kwargs["member_id"]
        self.subs = get_active_and_future_subscriptions(
            self.start_date, cache=self.cache
        ).filter(member_id=member_id, cancellation_ts__isnull=True)

        member = Member.objects.get(id=member_id)
        send_product_order_confirmation(
            member,
            self.subs,
            cache=self.cache,
            from_waiting_list=False,
            coop_share_transaction=None,
        )


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
