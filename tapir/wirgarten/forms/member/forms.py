from importlib.resources import _

from django.forms import (
    Form,
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
        orig_share_ownership = ShareOwnership.objects.get(member_id=member_id)

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
            + f" ({orig_share_ownership.quantity} Anteile)",
            disabled=True,
            initial=member_to_string(orig_member),
        )
        self.fields["receiver"] = ChoiceField(
            label=_("Empfänger der Genossenschaftsanteile"), choices=choices
        )
        self.fields["quantity"] = IntegerField(
            label=_("Anzahl der Anteile"),
            initial=orig_share_ownership.quantity,
            min_value=1,
            max_value=orig_share_ownership.quantity,
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
        self.fields["email"] = CharField(label=_("Email"))
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
