from django import forms
from icecream import ic

from tapir.accounts.models import EmailChangeRequest


class AdminMailChangeForm(forms.Form):
    user_id = forms.CharField(widget=forms.HiddenInput())
    new_email = forms.CharField(widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        ic(cleaned_data)
        if not EmailChangeRequest.objects.filter(
            user_id=cleaned_data["user_id"], new_email=cleaned_data["new_email"]
        ).exists():
            raise forms.ValidationError("Email change request not found.")

        return cleaned_data
