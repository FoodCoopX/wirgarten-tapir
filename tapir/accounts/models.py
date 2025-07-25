import logging
from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakDeleteError
from nanoid import generate
from phonenumber_field.modelfields import PhoneNumberField

from tapir import utils
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.core.models import ID_LENGTH, TapirModel, generate_id
from tapir.log.models import TextLogEntry, UpdateModelLogEntry
from tapir.settings import DEBUG
from tapir.utils.models import CountryField
from tapir.utils.user_utils import UserUtils

log = logging.getLogger(__name__)


class KeycloakUserQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        for obj in self:
            obj.delete()

        super().delete(*args, **kwargs)


class KeycloakUserQuerySetManager(models.Manager.from_queryset(KeycloakUserQuerySet)):
    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()


class KeycloakUser(AbstractUser):
    class Meta:
        abstract = True

    objects = KeycloakUserQuerySetManager()

    _kc: KeycloakAdmin = None
    roles: [str] = []
    email_verified = False

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

    def email_verified(self, cache: dict = None) -> bool:
        if cache is None:
            cache = {}
        kc = KeycloakUserManager.get_keycloak_client(cache=cache)
        try:
            kc_user = kc.get_user(self.keycloak_id)
            return kc_user["emailVerified"]
        except Exception:
            return False

    def send_verify_email(self, cache: dict):
        kc = KeycloakUserManager.get_keycloak_client(cache=cache)
        kc.send_verify_email(
            user_id=self.keycloak_id,
            redirect_uri=settings.SITE_URL,
            client_id=settings.KEYCLOAK_ADMIN_CONFIG["FRONTEND_CLIENT_ID"],
        )
        TextLogEntry().populate(
            text='Keycloak Email gesendet: "Aktivierung des Benutzerkontos"', user=self
        ).save()

    def has_perm(self, perm, obj=None):
        if DEBUG and self.is_superuser:
            return True
        return perm in self.roles

    @transaction.atomic
    def save(self, *args, **kwargs):
        bypass = kwargs.pop("bypass_keycloak", False)
        initial_password = kwargs.pop("initial_password", None)
        cache = kwargs.pop("cache", {})

        if not self.email:
            print(f"{self} has no email address, skipping keycloak account creation.")
            super().save(*args, **kwargs)
            return
        if bypass:
            print(f"{self}: bypass_keycloak=True, skipping keycloak account creation.")
            super().save(*args, **kwargs)
            return

        keycloak_client = KeycloakUserManager.get_keycloak_client(cache=cache)
        has_kc_account = self.keycloak_id is not None
        if has_kc_account:
            try:  # try fetch the keycloak user to see if it exists
                keycloak_client.get_user(self.keycloak_id)
            except:
                has_kc_account = False

        if has_kc_account:
            self_before_save = type(self).objects.get(id=self.id)
            transaction.on_commit(
                partial(
                    KeycloakUserManager.update_keycloak_user,
                    user=self,
                    keycloak_client=keycloak_client,
                    old_first_name=self_before_save.first_name,
                    old_last_name=self_before_save.last_name,
                    old_email=self_before_save.email,
                    new_first_name=self.first_name,
                    new_last_name=self.last_name,
                    new_email=self.email,
                    cache=cache,
                )
            )
            # important: reset the email to the original email before persisting. The actual change happens after the user click the confirmation link
            self.email = self_before_save.email
        else:
            KeycloakUserManager.create_keycloak_user(
                user=self,
                keycloak_client=keycloak_client,
                initial_password=initial_password,
                cache=cache,
            )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kc = KeycloakUserManager.get_keycloak_client(cache=kwargs.pop("cache", {}))
        if self.keycloak_id:
            try:
                kc.delete_user(self.keycloak_id)
            except KeycloakDeleteError as e:
                print("Error deleting Keycloak user: ", e)
        super().delete(*args, **kwargs)

    def change_email(self, new_email: str, cache: dict):
        kc = KeycloakUserManager.get_keycloak_client(cache=cache)
        kc.update_user(
            user_id=self.keycloak_id,
            payload={
                "email": new_email,
            },
        )


class TapirUser(KeycloakUser):
    first_name = models.CharField(_("First Name"), max_length=150, blank=False)
    last_name = models.CharField(_("Last Name"), max_length=150, blank=False)
    email = models.CharField(_("Email"), max_length=150, blank=True)
    phone_number = PhoneNumberField(_("Phone number"), blank=True, null=True)
    birthdate = models.DateField(_("Birthdate"), blank=True, null=True)
    street = models.CharField(_("Street and house number"), max_length=150, blank=True)
    street_2 = models.CharField(_("Extra address line"), max_length=150, blank=True)
    postcode = models.CharField(_("Postcode"), max_length=32, blank=True)
    city = models.CharField(_("City"), max_length=50, blank=True)
    country = CountryField(_("Country"), blank=True, default="DE")

    preferred_language = models.CharField(
        _("Preferred Language"),
        choices=utils.models.PREFERRED_LANGUAGES,
        default="de",
        max_length=16,
    )

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.username = self.email
        super().save(*args, **kwargs)  # call the parent save method

    @transaction.atomic
    def change_email(self, new_email: str, cache: dict):
        TapirUser.objects.filter(id=self.id).update(email=new_email, username=new_email)
        super().change_email(new_email, cache=cache)

    def get_display_name(self):
        return UserUtils.build_display_name(self.first_name, self.last_name)

    def get_display_address(self):
        return UserUtils.build_display_address(
            self.street, self.street_2, self.postcode, self.city
        )

    def get_absolute_url(self):
        return reverse("wirgarten:member_detail", args=[self.pk])

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    def has_perms(self, perms):
        for perm in perms:
            if not self.has_perm(perm, self):
                return False
        return True


def generate_random_secret():
    return generate(size=36)


class EmailChangeRequest(TapirModel):
    user = models.ForeignKey(TapirUser, on_delete=models.DO_NOTHING, null=False)
    new_email = models.CharField(_("New Email"), max_length=150, blank=False)
    secret = models.CharField(
        _("Secret"), max_length=36, default=partial(generate_random_secret)
    )
    created_at = models.DateTimeField(auto_now_add=True, null=False)


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
