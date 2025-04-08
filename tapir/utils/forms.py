from datetime import date

from django import forms
from django.forms import Form
from django.utils import formats
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberInternationalFallbackWidget

from tapir.utils.config import Organization


class DateInput(forms.DateInput):
    input_type = "date"

    def format_value(self, value: date):
        return formats.localize_input(value, "%Y-%m-%d")


class TapirPhoneNumberField(PhoneNumberField):

    widget = PhoneNumberInternationalFallbackWidget

    def __init__(self, *args, **kwargs):
        help_text = _(
            "German phone number don't need a prefix (e.g. (0)1736160646), international always (e.g. +12125552368)"
        )
        super(TapirPhoneNumberField, self).__init__(
            *args, help_text=help_text, **kwargs
        )


class ResetTestDataForm(Form):
    generate_test_data_for = forms.ChoiceField(
        choices=[(org.name, org.value) for org in Organization]
    )
    confirmation = forms.BooleanField(
        required=True,
        label=_("I understand what I am doing"),
        help_text=_(
            "This will delete all existing data, including members, users, subscriptions... and recreate them from scratch."
        ),
    )
