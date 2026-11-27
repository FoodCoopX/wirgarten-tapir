from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import FormView, TemplateView
from tapir.accounts.services.email_normaliser import EmailNormaliser
from tapir.mail.config import TransactionalTriggerKeys
from tapir.mail.forms import RegisterToMailCategoryForm
from tapir.mail.models import (
    MailCategory,
    ExternalRecipient,
    ExternalRecipientConfirmation,
)
from tapir.mail.services.external_recipient_manager import ExternalRecipientManager
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)
from tapir.wirgarten.utils import get_now


@method_decorator(xframe_options_exempt, name="dispatch")
class RegisterToMailCategoryView(FormView):
    # Limits how often the public form can make Tapir send a confirmation mail to the same address.
    CONFIRMATION_MAIL_COOLDOWN_SECONDS = 15 * 60

    form_class = RegisterToMailCategoryForm
    template_name = "tapir_mail/external.html"

    def __init__(self):
        super().__init__()
        self.category = None

    def get_category(self):
        if self.category is None:
            self.category = get_object_or_404(
                MailCategory,
                id=self.kwargs["category_id"],
                available_for_external_recipients=True,
            )

        return self.category

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["category_name"] = self.get_category().name
        return context_data

    def get_success_url(self):
        return reverse(
            "confirmation_mail_sent",
            args=[self.get_category().id],
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        email_address = EmailNormaliser.normalise(form.cleaned_data["email"])
        first_name = form.cleaned_data["first_name"]

        # Both cases end on the same page as a successful registration, so that the
        # form reveals neither registered addresses nor the cooldown.
        if ExternalRecipientManager.is_email_address_registered_to_category(
            mail_category=self.get_category(), email=email_address
        ):
            return response
        if not self._claim_confirmation_mail_cooldown(email_address=email_address):
            return response

        external_recipient, _ = ExternalRecipient.objects.get_or_create(
            email=email_address, defaults={"first_name": first_name}
        )
        external_recipient_confirmation, _ = (
            ExternalRecipientConfirmation.objects.get_or_create(
                external_recipient=external_recipient, mail_category=self.get_category()
            )
        )
        self.external_recipient_confirmation = external_recipient_confirmation

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=TransactionalTriggerKeys.MAIL_CATEGORY_REGISTRATION_CONFIRMATION_LINK,
                token_data={
                    "category_name": self.get_category().name,
                    "confirmation_link": settings.SITE_URL
                    + reverse(
                        "user_confirms_registration",
                        args=[external_recipient_confirmation.confirmation_secret],
                    ),
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=email_address, first_name=first_name, last_name=""
                ),
            )
        )

        return response

    def _claim_confirmation_mail_cooldown(self, email_address: str) -> bool:
        cache_key = f"mail_category_registration_confirmation:{self.get_category().id}:{email_address.strip().lower()}"
        return cache.add(
            cache_key, True, timeout=self.CONFIRMATION_MAIL_COOLDOWN_SECONDS
        )


@method_decorator(xframe_options_exempt, name="get")
class ConfirmationMailSentView(TemplateView):
    template_name = "tapir_mail/confirmation_mail_sent.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["category_name"] = get_object_or_404(
            MailCategory, id=self.kwargs["category_id"]
        ).name
        return context_data


class ConfirmRegistrationToMailCategoryView(TemplateView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.external_recipient_confirmation = get_object_or_404(
            ExternalRecipientConfirmation, confirmation_secret=kwargs["secret"]
        )

    def get_template_names(self):
        if self.external_recipient_confirmation.confirmed_at is None:
            return ["tapir_mail/confirm_registration.html"]
        return ["tapir_mail/confirmation_registration_complete.html"]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if self.external_recipient_confirmation.confirmed_at is None:
            self._confirm_registration()
        return redirect(request.path)

    def _confirm_registration(self):
        external_recipient_confirmation = self.external_recipient_confirmation
        external_recipient_confirmation.confirmed_at = get_now(cache={})
        external_recipient_confirmation.save()

        ExternalRecipientManager.register_external_recipient_to_category(
            mail_category=external_recipient_confirmation.mail_category,
            external_recipient=external_recipient_confirmation.external_recipient,
        )

        external_recipient = external_recipient_confirmation.external_recipient
        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=TransactionalTriggerKeys.MAIL_CATEGORY_REGISTRATION_CONFIRMED,
                token_data={
                    "category_name": external_recipient_confirmation.mail_category.name,
                    "management_link": settings.SITE_URL
                    + reverse("core:subscription_management_link_request"),
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=external_recipient.email,
                    first_name=external_recipient.first_name,
                    last_name="",
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["mail_category_name"] = (
            self.external_recipient_confirmation.mail_category.name
        )
        return context_data
