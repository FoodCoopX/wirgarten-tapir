from importlib.resources import _

from django import forms

from tapir.utils.forms import TapirPhoneNumberField, DateInput
from tapir.wirgarten.models import Member


class PersonalDataForm(forms.ModelForm):
    n_columns = 2

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
        required = [field for field in fields if field != "street_2"]
        widgets = {"birthdate": DateInput()}

    phone_number = TapirPhoneNumberField(label=_("Telefon-Nr"))
