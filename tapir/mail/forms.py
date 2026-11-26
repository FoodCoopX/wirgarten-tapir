from django import forms
from django.forms.forms import Form

from tapir.mail.models import MailCategory, ExternalRecipient
from tapir.mail.service.external_recipient_manager import ExternalRecipientManager


class RegisterToMailCategoryForm(Form):
    email = forms.EmailField(required=True, label="E-Mail-Adresse")
    first_name = forms.CharField(required=True, label="Vorname")


class ExternalRecipientManagementForm(Form):
    first_name = forms.CharField(label="Vorname")

    def __init__(self, *args, **kwargs):
        self.external_recipient: ExternalRecipient = kwargs.pop("external_recipient")

        super().__init__(*args, **kwargs)

        self.fields["first_name"].initial = self.external_recipient.first_name

        for mail_category in MailCategory.objects.filter(
            available_for_external_recipients=True
        ).order_by("name"):
            is_registered = (
                ExternalRecipientManager.is_email_address_registered_to_category(
                    mail_category=mail_category, email=self.external_recipient.email
                )
            )
            self.fields[self.build_field_key_for_category(mail_category)] = (
                forms.BooleanField(
                    label=mail_category.name, initial=is_registered, required=False
                )
            )

    @staticmethod
    def build_field_key_for_category(mail_category: MailCategory):
        return "category_" + mail_category.id
