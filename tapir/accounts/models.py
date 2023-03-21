import base64
import json
import logging
from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from keycloak import (
    KeycloakAdmin,
)
from keycloak.exceptions import KeycloakDeleteError
from nanoid import generate
from phonenumber_field.modelfields import PhoneNumberField

from tapir import utils
from tapir.core.models import generate_id, ID_LENGTH, TapirModel
from tapir.log.models import UpdateModelLogEntry
from tapir.utils.models import CountryField
from tapir.utils.user_utils import UserUtils
from tapir.wirgarten.service.email import send_email

log = logging.getLogger(__name__)


class KeycloakUserQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        for obj in self:
            obj.delete()

        super().delete(*args, **kwargs)


class KeycloakUserManager(models.Manager.from_queryset(KeycloakUserQuerySet)):
    def normalize_email(self, email: str) -> str:
        return email.strip()


class KeycloakUser(AbstractUser):
    objects = KeycloakUserManager()

    _kk: KeycloakAdmin = None
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

    def email_verified(self):
        kk = self.get_keycloak_client()
        kk_user = kk.get_user(self.keycloak_id)
        return kk_user["emailVerified"]

    def get_keycloak_client(self):
        # FIXME: can we keep one instance? It seemed that the authorization expires, but not sure yet
        # if not self._kk or self._kk.is_authenticated():
        config = settings.KEYCLOAK_ADMIN_CONFIG

        return KeycloakAdmin(
            server_url=config["SERVER_URL"] + "/auth",
            client_id=config["CLIENT_ID"],
            realm_name=config["REALM_NAME"],
            user_realm_name=config["USER_REALM_NAME"],
            client_secret_key=config["CLIENT_SECRET_KEY"],
            verify=True,
        )

        # return self._kk

    def send_verify_email(self):
        kk = self.get_keycloak_client()
        kk.send_verify_email(
            user_id=self.keycloak_id,
            redirect_uri=settings.SITE_URL,
            client_id=settings.KEYCLOAK_ADMIN_CONFIG["FRONTEND_CLIENT_ID"],
        )

    def has_perm(self, perm, obj=None):
        return perm in self.roles

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.keycloak_id is None:  # Keycloak User does not exist yet --> create
            kk = self.get_keycloak_client()

            data = {
                "username": self.email,
                "email": self.email,
                "firstName": self.first_name,
                "lastName": self.last_name,
                "enabled": True,
            }
            print("Creating Keycloak user: ", data)

            initial_password = kwargs.pop("initial_password", None)
            if initial_password:
                data["credentials"] = [{"value": initial_password, "type": "password"}]
                data["emailVerified"] = True
            else:
                data["requiredActions"] = ["VERIFY_EMAIL", "UPDATE_PASSWORD"]

            if self.is_superuser:
                group = kk.get_group_by_path(path="/superuser")
                if group:
                    data["groups"] = ["superuser"]

            self.keycloak_id = kk.create_user(data)

            try:
                self.send_verify_email()
            except Exception as e:
                # FIXME: schedule to try again later?
                print(
                    f"Failed to send verify email to new user: ",
                    e,
                    " (email: '{self.email}', id: '{self.id}', keycloak_id: '{user_id}'): ",
                )

        else:  # Update --> change of keycloak data if necessary
            original = type(self).objects.get(id=self.id)
            email_changed = original.email != self.email
            first_name_changed = original.first_name != self.first_name
            last_name_changed = original.last_name != self.last_name

            kk = self.get_keycloak_client()
            if first_name_changed or last_name_changed:
                data = {"firstName": self.first_name, "lastName": self.last_name}
                kk.update_user(user_id=self.keycloak_id, payload=data)

            if email_changed:
                if self.email_verified():
                    self.start_email_change_process(self.email)
                    # important: reset the email to the original email before persisting. The actual change happens after the user click the confirmation link
                    self.email = original.email
                else:  # in this case, don't start the email change process, just send the keycloak email to the new address and resend the link
                    kk.update_user(
                        user_id=self.keycloak_id, payload={"email": self.email}
                    )
                    self.send_verify_email()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kk = self.get_keycloak_client()
        if self.keycloak_id:
            try:
                kk.delete_user(self.keycloak_id)
            except KeycloakDeleteError as e:
                print("Error deleting Keycloak user: ", e)
        super().delete(*args, **kwargs)

    def change_email(self, new_email: str):
        kk = self.get_keycloak_client()
        kk.update_user(
            user_id=self.keycloak_id,
            payload={
                "email": new_email,
            },
        )

    @transaction.atomic
    def start_email_change_process(self, new_email: str):
        EmailChangeRequest.objects.filter(user_id=self.id).delete()
        email_change_request = EmailChangeRequest.objects.create(
            new_email=new_email, user_id=self.id
        )
        email_change_token = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "new_email": email_change_request.new_email,
                    "secret": email_change_request.secret,
                    "user": email_change_request.user_id,
                }
            ).encode()
        ).decode()

        send_email(
            to_email=[new_email],
            subject=_("Änderung deiner Email-Adresse"),
            content=f"Hallo {self.first_name},<br/><br/>"
            f"du hast gerade die Email Adresse für deinen WirGarten Account geändert.<br/><br/>"
            f"Bitte klicke den folgenden Link um die Änderung zu bestätigen:<br/>"
            f"""<a target="_blank", href="{settings.SITE_URL}{reverse_lazy('change_email_confirm', kwargs={"token": email_change_token})}"><strong>Email Adresse bestätigen</strong></a><br/><br/>"""
            f"Falls du das nicht warst, kannst du diese Mail einfach löschen oder ignorieren."
            f"<br/><br/>Grüße, dein WirGarten Team",
        )

    class Meta:
        abstract = True


class TapirUser(KeycloakUser):
    first_name = models.CharField(_("First Name"), max_length=150, blank=False)
    last_name = models.CharField(_("Last Name"), max_length=150, blank=False)
    email = models.CharField(_("Email"), max_length=150, blank=False)
    phone_number = PhoneNumberField(_("Phone number"), blank=True)
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
    def change_email(self, new_email: str):
        TapirUser.objects.filter(id=self.id).update(email=new_email, username=new_email)
        super().change_email(new_email)

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
