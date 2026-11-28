from django import forms
from django.forms.forms import Form


class RegisterToMailCategoryForm(Form):
    email = forms.EmailField(required=True, label="E-Mail-Adresse")
    first_name = forms.CharField(required=True, label="Vorname")
