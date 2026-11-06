import uuid
from decimal import Decimal

from django import forms
from django.core.validators import MaxValueValidator

from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.utils.forms import DateInput
from tapir.wirgarten.models import Member


class DepositMemberChoiceForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=Member.objects.order_by("last_name", "first_name", "pk"),
        label="Mitglied auswählen",
    )


class DepositAgreementForm(forms.Form):
    amount = forms.DecimalField(
        label="Vereinbarter Gesamtbetrag (€)",
        max_digits=8,
        decimal_places=2,
        min_value=0,
    )
    effective_from = forms.DateField(label="Frühester Einzug ab", widget=DateInput())
    instalment_count = forms.IntegerField(
        label="Anzahl monatlicher Raten",
        min_value=1,
        max_value=AssociationDepositInstalmentCalculator.MAX_INSTALMENTS,
        help_text="Bei 0 € bitte 1 wählen; es wird keine Zahlung angelegt. Der rechnerisch verbleibende Betrag nach erfassten Rückzahlungen wird angerechnet.",
    )
    consented_on = forms.DateField(label="Zustimmung vom", widget=DateInput())
    consent_note = forms.CharField(
        label="Dokumentierte Zustimmung",
        widget=forms.Textarea(attrs={"rows": 3}),
        max_length=3000,
    )
    expected_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput())
    request_key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput())


class DepositReceiptForm(forms.Form):
    expected_committed_amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, widget=forms.HiddenInput()
    )
    amount = forms.DecimalField(
        label="Erhaltener Betrag (€)",
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    received_on = forms.DateField(label="Eingangsdatum", widget=DateInput())
    reference = forms.CharField(
        label="Eindeutige Bank-Buchungsreferenz",
        max_length=100,
        help_text="Identische Wiederholungen werden nicht erneut gutgeschrieben.",
    )
    note = forms.CharField(
        label="Beleg / Anmerkung",
        widget=forms.Textarea(attrs={"rows": 2}),
        max_length=3000,
    )


class DepositRefundForm(forms.Form):
    amount = forms.DecimalField(
        label="Bereits zurückgezahlter Betrag (€)",
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    refunded_on = forms.DateField(label="Rückzahlungsdatum", widget=DateInput())
    reference = forms.CharField(
        label="Eindeutige Bank-Buchungsreferenz", max_length=100
    )
    note = forms.CharField(
        label="Beleg / Anmerkung",
        widget=forms.Textarea(attrs={"rows": 2}),
        max_length=3000,
    )
    bank_settlement_confirmed = forms.BooleanField(
        label="Die Rückzahlung ist ausgeführt. Die zugrundeliegenden Einzahlungen einschließlich SEPA-Eingängen sind bankseitig geprüft."
    )
    expected_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput())
    expected_committed_amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, widget=forms.HiddenInput()
    )


class DepositDepartureReportForm(forms.Form):
    year = forms.IntegerField(
        label="Jahr des letzten wirksamen Austritts", min_value=1900
    )

    def __init__(self, *args, reference_date, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["year"].max_value = reference_date.year
        self.fields["year"].validators.append(MaxValueValidator(reference_date.year))
        self.fields["year"].widget.attrs["max"] = reference_date.year
