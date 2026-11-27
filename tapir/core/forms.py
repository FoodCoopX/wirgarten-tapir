from django import forms


class SubscriptionManagementLinkRequestForm(forms.Form):
    email = forms.EmailField(label="E-Mail-Adresse")
