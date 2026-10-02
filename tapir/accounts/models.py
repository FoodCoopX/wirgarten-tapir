import logging
from functools import partial

from django.contrib.auth import user_logged_out
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.dispatch import receiver
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from nanoid import generate
from phonenumber_field.modelfields import PhoneNumberField
from tapir_mail.models import StaticSegmentRecipient

from tapir import utils
from tapir.core.models import ID_LENGTH, TapirModel, generate_id
from tapir.log.models import TextLogEntry, UpdateModelLogEntry
from tapir.utils.models import CountryField
from tapir.utils.shortcuts import is_running_tests
from tapir.utils.user_utils import UserUtils

LOG = logging.getLogger(__name__)


class KeycloakUser(AbstractUser):
    class Meta:
        abstract = True

    id = models.CharField(
        "ID",
        max_length=ID_LENGTH,
        unique=True,
        primary_key=True,
        default=partial(generate_id),
    )
    keycloak_id = models.CharField(
        max_length=64, unique=True, primary_key=False, null=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.roles = None

    def has_perm(self, perm, obj=None):
        if is_running_tests():
            return self.is_superuser

        target = self
        if obj is not None:
            target = obj

        if target.roles is None:
            from tapir.accounts.services.keycloak_user_manager import (
                KeycloakUserManager,
            )

            target.roles = KeycloakUserManager.get_user_roles(
                keycloak_id=target.keycloak_id
            )

        return perm in target.roles

    def has_perms(self, perm_list, obj=None):
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True


class TapirUser(KeycloakUser):
    first_name = models.CharField(_("First Name"), max_length=150, blank=False)
    last_name = models.CharField(_("Last Name"), max_length=150, blank=False)
    email = models.CharField(_("Email"), max_length=150, blank=True)
    phone_number = PhoneNumberField(_("Phone number"), blank=True, null=True)
    phone_number_landline = PhoneNumberField(
        _("Phone number (landline)"), blank=True, null=True
    )
    birthdate = models.DateField(_("Birthdate"), blank=True, null=True)
    street = models.CharField(_("Street and house number"), max_length=150, blank=True)
    street_2 = models.CharField(_("Extra address line"), max_length=150, blank=True)
    postcode = models.CharField(_("Postcode"), max_length=32, blank=True)
    city = models.CharField(_("City"), max_length=50, blank=True)
    country = CountryField(_("Country"), blank=True, default="DE")
    form_of_address = models.CharField(
        _("Liebe/Lieber"), max_length=20, blank=True, null=True
    )

    preferred_language = models.CharField(
        _("Preferred Language"),
        choices=utils.models.PREFERRED_LANGUAGES,
        default="de",
        max_length=16,
    )

    def get_display_name(self):
        return UserUtils.build_display_name(self.first_name, self.last_name)

    def get_display_address(self):
        return UserUtils.build_display_address(
            self.street, self.street_2, self.postcode, self.city
        )

    def get_absolute_url(self):
        return reverse("wirgarten:member_detail", args=[self.pk])


@receiver(user_logged_out)
def terminate_session(sender, request, user, **kwargs):
    if user is None:
        return

    from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager

    keycloak_client = KeycloakUserManager.get_keycloak_client(cache={})
    keycloak_client.user_logout(user.keycloak_id)


def generate_random_secret():
    return generate(size=36)


class EmailChangeRequest(TapirModel):
    user = models.ForeignKey(TapirUser, on_delete=models.DO_NOTHING, null=False)
    new_email = models.CharField(_("New Email"), max_length=150, blank=False)
    secret = models.CharField(
        _("Secret"), max_length=36, default=partial(generate_random_secret)
    )


class UpdateTapirUserLogEntry(UpdateModelLogEntry):
    template_name = "accounts/log/update_tapir_user_log_entry.html"
    excluded_fields = ["password"]


def language_middleware(get_response):
    def middleware(request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            translation.activate(user.preferred_language)
        response = get_response(request)
        translation.deactivate()
        return response

    return middleware
