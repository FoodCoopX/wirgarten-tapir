import localflavor
from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from localflavor.generic.validators import IBANValidator, BICValidator

from tapir.coop.models import (
    ShareOwnership,
    DraftUser,
    ShareOwner,
    FinancingCampaign,
    COOP_MINIMUM_SHARES,
    COOP_SHARE_PRICE,
)
from tapir.utils.forms import DateInput, TapirPhoneNumberField


class ShareOwnershipForm(forms.ModelForm):
    class Meta:
        model = ShareOwnership
        fields = [
            "start_date",
            "end_date",
            "amount_paid",
        ]
        widgets = {
            "start_date": DateInput(),
            "end_date": DateInput(),
        }


class PaymentUserDataMixin(forms.Form):
    account_owner = forms.CharField(label=_("Account owner"))
    iban = forms.CharField(label=_("IBAN"))
    bic = forms.CharField(label=_("BIC"))

    def get_initial_for_field(self, field, field_name):
        if self.instance is None:
            return

        if field_name in ["account_owner", "iban", "bic"]:
            return getattr(self.instance, field_name)
        else:
            return super().get_initial_for_field(field, field_name)

    def clean_iban(self):
        # Théo 17.03.22 : I tried just putting iban and bic as fields in the Meta class,
        # I was getting django errors that I didn't manage to solve, so I made them manually.
        iban = self.cleaned_data["iban"]
        try:
            IBANValidator()(iban)
        except localflavor.exceptions.ValidationError:
            self.add_error("iban", _("Invalid IBAN"))
        return iban

    def clean_bic(self):
        bic = self.cleaned_data["bic"]
        try:
            BICValidator()(bic)
        except localflavor.exceptions.ValidationError:
            self.add_error("bic", _("Invalid BIC"))
        return bic

    def save_payment_user_data(self, user):
        user.account_owner = self.cleaned_data["account_owner"]
        user.iban = self.cleaned_data["iban"]
        user.bic = self.cleaned_data["bic"]
        user.save()

    def save(self, commit=True):
        instance = super().save(commit)
        self.save_payment_user_data(instance)
        return instance


class DraftUserLimitedForm(PaymentUserDataMixin, forms.ModelForm):
    class Meta:
        model = DraftUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "birthdate",
            "street",
            "street_2",
            "postcode",
            "city",
            "country",
            "preferred_language",
            "num_shares",
        ]
        required = [field for field in fields if field != "street_2"]
        widgets = {"birthdate": DateInput()}
        labels = {
            "num_shares": _(
                f"Per Satzung bist du verpflichtet, mindestens {COOP_MINIMUM_SHARES} Anteile a {COOP_SHARE_PRICE} € zeichnen. Je mehr Genossenschaftsanteile du zeichnest, desto solider kann die Infrastruktur deines WirGartens finanziert werden."
            ),
        }

    phone_number = TapirPhoneNumberField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.Meta.required:
            self.fields[field].required = True

        if kwargs.get("instance") is None:
            self.fields["accept_sepa"] = forms.BooleanField(
                label=_(
                    "Ich ermächtige die WirGarten Lüneburg eG die gezeichneten Geschäftsanteile mittels Lastschrift von meinem Bankkonto einzuziehen. Zugleich weise ich mein Kreditinstitut an, die gezogene Lastschrift einzulösen."
                )
            )
            self.fields["accept_statutes"] = forms.BooleanField(
                label=mark_safe(
                    _(
                        "Ja, ich habe die Satzung und die Kündigungsfrist von einem Jahr zum Jahresende unter <a href='https://lueneburg.wirgarten.com/satzung/'>https://lueneburg.wirgarten.com/satzung/</a> zur Kenntnis genommen."
                    )
                )
            )
            self.fields["right_of_withdrawal"] = forms.BooleanField(
                label=_("Ja, ich habe die Widerrufsbelehrung zur Kenntnis genommen.")
            )

    def clean_num_shares(self):
        num_shares = self.cleaned_data["num_shares"]
        if num_shares < COOP_MINIMUM_SHARES:
            self.add_error(
                "num_shares",
                _(f"The minimum amount of shares is {COOP_MINIMUM_SHARES}."),
            )
        return num_shares


class DraftUserFullForm(DraftUserLimitedForm):
    class Meta(DraftUserLimitedForm.Meta):
        model = DraftUser
        fields = DraftUserLimitedForm.Meta.fields + [
            "is_investing",
            "attended_welcome_session",
            "ratenzahlung",
            "paid_membership_fee",
            "paid_shares",
            "signed_membership_agreement",
        ]
        widgets = {
            "birthdate": DateInput(),
        }


class ShareOwnerForm(PaymentUserDataMixin, forms.ModelForm):
    class Meta:
        model = ShareOwner
        fields = [
            "is_company",
            "company_name",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "birthdate",
            "street",
            "street_2",
            "postcode",
            "city",
            "preferred_language",
            "is_investing",
            "ratenzahlung",
            "attended_welcome_session",
            "paid_membership_fee",
            "willing_to_gift_a_share",
        ]
        widgets = {
            "birthdate": DateInput(),
            "willing_to_gift_a_share": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.user:
            for f in [
                "is_company",
                "company_name",
                "first_name",
                "last_name",
                "email",
                "birthdate",
                "street",
                "street_2",
                "postcode",
                "city",
                "preferred_language",
                "phone_number",
            ]:
                del self.fields[f]


class FinancingCampaignForm(forms.ModelForm):
    class Meta:
        model = FinancingCampaign
        fields = [
            "name",
            "is_active",
            "goal",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for source in self.instance.sources.all():
            self.fields[f"financing_source_{source.id}"] = forms.IntegerField(
                required=True, label=_(source.name), initial=source.raised_amount
            )

    def save(self, commit=True):
        for source in self.instance.sources.all():
            source.raised_amount = self.cleaned_data[f"financing_source_{source.id}"]
            source.save()
        return super().save(commit=commit)
