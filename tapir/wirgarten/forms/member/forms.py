from datetime import datetime
from importlib.resources import _

from django.core.mail import EmailMultiAlternatives
from django.core.validators import (
    EmailValidator,
)
from django.db import transaction
from django.db.models import Sum
from django.forms import (
    Form,
    CheckboxInput,
    ModelForm,
    BooleanField,
    DecimalField,
    CharField,
    ChoiceField,
    IntegerField,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.forms import TapirPhoneNumberField, DateInput
from tapir.wirgarten.models import Payment, Member, ShareOwnership
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import (
    get_subscriptions_in_trial_period,
    get_next_trial_end_date,
)
from tapir.wirgarten.utils import format_date


class PersonalDataForm(ModelForm):
    n_columns = 2

    def __init__(self, *args, **kwargs):
        super(PersonalDataForm, self).__init__(*args, **kwargs)
        for k, v in self.fields.items():
            if k != "street_2":
                v.required = True

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
        ]
        widgets = {"birthdate": DateInput()}

    phone_number = TapirPhoneNumberField(label=_("Telefon-Nr"))


class PaymentAmountEditForm(Form):
    def __init__(self, *args, **kwargs):
        super(PaymentAmountEditForm, self).__init__(*args)

        self.mandate_ref_id = kwargs["mandate_ref_id"].replace("~", "/")
        self.payment_due_date = kwargs["payment_due_date"]

        payments = Payment.objects.filter(
            mandate_ref=self.mandate_ref_id, due_date=self.payment_due_date
        )

        if len(payments) < 1:
            initial = 0.00
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
        orig_share_ownership_quantity = ShareOwnership.objects.filter(
            member_id=member_id
        ).aggregate(quantity_sum=Sum("quantity"))["quantity_sum"]

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
            + f" ({orig_share_ownership_quantity} Anteile)",
            disabled=True,
            initial=member_to_string(orig_member),
        )
        self.fields["receiver"] = ChoiceField(
            label=_("Empfänger der Genossenschaftsanteile"), choices=choices
        )
        self.fields["quantity"] = IntegerField(
            label=_("Anzahl der Anteile"),
            initial=orig_share_ownership_quantity,
            min_value=1,
            max_value=orig_share_ownership_quantity,
        )
        self.fields["security_check"] = BooleanField(
            label=_("Ich weiß was ich tue und bin mir der Konsequenzen bewusst."),
            required=True,
        )


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
        self.fields["privacy_consent"] = BooleanField(
            label=_("Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen."),
            required=True,
            help_text=_(
                'Wir behandeln deine Daten vertraulich, verwenden diese nur im Rahmen der Mitgliederverwaltung und geben sie nicht an Dritte weiter. Unsere Datenschutzerklärung kannst du hier einsehen: <a target="_blank" href="{privacy_link}">Datenschutzerklärung - {site_name}</a>'
            ).format(
                site_name=get_parameter_value(Parameter.SITE_NAME),
                privacy_link=get_parameter_value(Parameter.SITE_PRIVACY_LINK),
            ),
        )


class TrialCancellationForm(Form):
    KEY_PREFIX = "sub_"
    BASE_PROD_TYPE_ATTR = "data-base-product-type"

    template_name = "wirgarten/member/trial_cancellation_form.html"

    def __init__(self, *args, **kwargs):
        self.member_id = kwargs.pop("pk")
        super(TrialCancellationForm, self).__init__(*args, **kwargs)

        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        self.subs = get_subscriptions_in_trial_period(self.member_id)
        self.next_trial_end_date = get_next_trial_end_date()

        def is_new_member() -> bool:
            try:
                self.share_ownership = ShareOwnership.objects.get(
                    member_id=self.member_id
                )
                return self.share_ownership.entry_date > self.next_trial_end_date
            except (
                ShareOwnership.DoesNotExist,
                ShareOwnership.MultipleObjectsReturned,
            ):
                return (
                    False  # new members should have exactly one share_ownership entity
                )

        for sub in self.subs:
            key = f"{self.KEY_PREFIX}{sub.id}"
            self.fields[key] = BooleanField(
                label=f"{sub.quantity} × {sub.product.name} {sub.product.type.name}",
                required=False,
            )
            if len(self.subs) > 1 and sub.product.type.id == base_product_type_id:
                self.fields[key].widget = CheckboxInput(
                    attrs={"data-base-product-type": "true"}
                )

        if is_new_member():
            self.fields["cancel_coop"] = BooleanField(
                label="Mitgliedschaftsantrag zurückziehen", required=False
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

    @transaction.atomic
    def save(self):
        cancel_coop = "cancel_coop" in self.cleaned_data and self.cleaned_data.pop(
            "cancel_coop"
        )
        subs_to_cancel = self.subs.filter(
            id__in=[
                key.replace("sub_", "")
                for key, value in self.cleaned_data.items()
                if value
            ]
        )
        now = datetime.now()
        for sub in subs_to_cancel:
            sub.cancellation_ts = now
            sub.end_date = self.next_trial_end_date
            sub.save()

        if cancel_coop and self.share_ownership:
            Payment.objects.get(
                mandate_ref=self.share_ownership.mandate_ref, due_date__gt=now
            ).delete()
            self.share_ownership.delete()  # TODO: create log entry

        # send confirmation email
        member = Member.objects.get(pk=self.member_id)
        email = EmailMultiAlternatives(
            subject=_("Kündigungsbestätigung"),
            body=_(
                f"Liebe/r {member.first_name},<br/><br/>"
                f""
                f"hiermit bestätigen wir dir die Kündigung deiner:<br/><br/>"
                f""
                f"{'<br/>'.join(map(lambda x: '- ' + str(x), subs_to_cancel))}<br/>"
                f""
                f"zum <strong>{format_date(self.next_trial_end_date)}</strong>.<br/><br/>"
                f"{get_parameter_value(Parameter.SITE_NAME)}"
            ),
            to=[member.email],
            from_email=get_parameter_value(Parameter.SITE_ADMIN_EMAIL),
        )
        email.content_subtype = "html"
        email.send()
