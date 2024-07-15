import base64
import json
import logging
from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.urls import reverse, reverse_lazy
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import KeycloakDeleteError
from nanoid import generate
from phonenumber_field.modelfields import PhoneNumberField
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir import utils
from tapir.core.models import ID_LENGTH, TapirModel, generate_id
from tapir.log.models import TextLogEntry, UpdateModelLogEntry
from tapir.utils.models import CountryField
from tapir.utils.user_utils import UserUtils

log = logging.getLogger(__name__)


class KeycloakUserQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        for obj in self:
            obj.delete()

        super().delete(*args, **kwargs)


class KeycloakUserManager(models.Manager.from_queryset(KeycloakUserQuerySet)):
    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip()


class KeycloakUser(AbstractUser):
    objects = KeycloakUserManager()

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

    def email_verified(self):
        kc = self.get_keycloak_client()
        try:
            kc_user = kc.get_user(self.keycloak_id)
            return kc_user["emailVerified"]
        except Exception:
            return False

    @classmethod
    def get_keycloak_client(self):
        if not self._kc:
            config = settings.KEYCLOAK_ADMIN_CONFIG

            keycloak_connection = KeycloakOpenIDConnection(
                server_url=config["SERVER_URL"],
                realm_name=config["REALM_NAME"],
                client_id=config["CLIENT_ID"],
                client_secret_key=config["CLIENT_SECRET_KEY"],
                verify=True,
            )

            self._kc = KeycloakAdmin(connection=keycloak_connection)

        return self._kc

    def send_verify_email(self):
        kc = self.get_keycloak_client()
        kc.send_verify_email(
            user_id=self.keycloak_id,
            redirect_uri=settings.SITE_URL,
            client_id=settings.KEYCLOAK_ADMIN_CONFIG["FRONTEND_CLIENT_ID"],
        )
        TextLogEntry().populate(
            text='Keycloak Email gesendet: "Aktivierung des Benutzerkontos"', user=self
        ).save()

    def has_perm(self, perm, obj=None):
        return perm in self.roles

    @transaction.atomic
    def save(self, *args, **kwargs):
        bypass = kwargs.pop("bypass_keycloak", False)
        initial_password = kwargs.pop("initial_password", None)

        if not self.email:
            print(f"{self} has no email address, skipping keycloak account creation.")
            super().save(*args, **kwargs)
            return
        if bypass:
            print(f"{self}: bypass_keycloak=True, skipping keycloak account creation.")
            super().save(*args, **kwargs)
            return

        kc = self.get_keycloak_client()
        has_kc_account = self.keycloak_id is not None
        if has_kc_account:
            try:  # try fetch the keycloak user to see if it exists
                kc.get_user(self.keycloak_id)
            except:
                has_kc_account = False

        if not has_kc_account:  # Keycloak User does not exist yet --> create
            data = {
                "username": self.email,
                "email": self.email,
                "firstName": self.first_name,
                "lastName": self.last_name,
                "enabled": True,
            }
            print("Creating Keycloak user: ", data)

            keycloak_id = kc.get_user_id(self.email)
            if keycloak_id is not None:
                if not TapirUser.objects.filter(keycloak_id=keycloak_id).exists():
                    self.keycloak_id = keycloak_id
                    kc.update_user(user_id=self.keycloak_id, payload=data)
            else:
                if initial_password:
                    data["credentials"] = [
                        {"value": initial_password, "type": "password"}
                    ]
                    data["emailVerified"] = True
                else:
                    data["requiredActions"] = ["VERIFY_EMAIL", "UPDATE_PASSWORD"]

                if self.is_superuser:
                    group = kc.get_group_by_path(path="/superuser")
                    if group:
                        data["groups"] = ["superuser"]

                self.keycloak_id = kc.create_user(data)

                try:
                    self.send_verify_email()
                except Exception as e:
                    print(
                        f"Failed to send verify email to new user: ",
                        e,
                        f" (email: '{self.email}', id: '{self.id}', keycloak_id: '{self.keycloak_id}'): ",
                    )

        else:  # Update --> change of keycloak data if necessary
            original = type(self).objects.get(id=self.id)
            email_changed = original.email != self.email
            first_name_changed = original.first_name != self.first_name
            last_name_changed = original.last_name != self.last_name

            if first_name_changed or last_name_changed:
                data = {"firstName": self.first_name, "lastName": self.last_name}
                kc.update_user(user_id=self.keycloak_id, payload=data)

            if email_changed:
                if self.email_verified():
                    self.start_email_change_process(self.email, original.email)
                    # important: reset the email to the original email before persisting. The actual change happens after the user click the confirmation link
                    self.email = original.email
                else:  # in this case, don't start the email change process, just send the keycloak email to the new address and resend the link
                    kc.update_user(
                        user_id=self.keycloak_id, payload={"email": self.email}
                    )
                    self.send_verify_email()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kc = self.get_keycloak_client()
        if self.keycloak_id:
            try:
                kc.delete_user(self.keycloak_id)
            except KeycloakDeleteError as e:
                print("Error deleting Keycloak user: ", e)
        super().delete(*args, **kwargs)

    def change_email(self, new_email: str):
        kc = self.get_keycloak_client()
        kc.update_user(
            user_id=self.keycloak_id,
            payload={
                "email": new_email,
            },
        )

    @transaction.atomic
    def start_email_change_process(self, new_email: str, orig_email: str):
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
        verify_link = f"{settings.SITE_URL}{reverse_lazy('change_email_confirm', kwargs={'token': email_change_token})}"

        from tapir.wirgarten.service.email import send_email
        from tapir.wirgarten.tapirmail import Events

        TransactionalTrigger.fire_action(
            Events.MEMBERAREA_CHANGE_EMAIL_INITIATE,
            orig_email,
            {"verify_link": verify_link},
        )

        send_email(
            to_email=[orig_email],
            subject=_("Änderung deiner Email-Adresse"),
            content=f"Hallo {self.first_name},<br/><br/>"
            f"du hast gerade die Email Adresse für deinen WirGarten Account geändert.<br/><br/>"
            f"Bitte klicke den folgenden Link um die Änderung zu bestätigen:<br/>"
            f"""<a target="_blank", href="{verify_link}"><strong>Email Adresse bestätigen</strong></a><br/><br/>"""
            f"Falls du das nicht warst, kannst du diese Mail einfach löschen oder ignorieren."
            f"<br/><br/>Grüße, dein WirGarten Team",
        )

    class Meta:
        abstract = True


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
