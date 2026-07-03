from imaplib import IMAP4_SSL

from django.conf import settings
from django.core import mail
from django.core.cache import cache as redis_cache
from django.test import Client
from django.urls import reverse
from nanoid.generate import generate

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.core.models import DatabaseWriteTest
from tapir.wirgarten.models import Member


class TapirHealthStatusProvider:
    @classmethod
    def get_health_status(cls) -> dict[str, str | bool]:
        status_checks = {
            "db": cls._get_db_status,
            "redis": cls._get_redis_status,
            "keycloak": cls._get_keycloak_status,
            "smtp_server": cls._get_smtp_connection_status,
            "bounce_mailbox": cls._get_bounce_mailbox_status,
            "order_wizard_base": cls._get_order_wizard_base_status,
            "order_wizard_data": cls._get_order_wizard_data_status,
            "member_profile": cls._get_member_profile_status,
        }

        statuses = {}
        for key, callback in status_checks.items():
            try:
                error = callback()
            except Exception as exception:
                error = repr(exception)
            statuses |= {
                key: error is None,
                f"{key}_error": error or "healthy",
            }

        return statuses

    @classmethod
    def _get_db_status(cls):
        test_object = DatabaseWriteTest.objects.create()
        DatabaseWriteTest.objects.get(id=test_object.id)
        test_object.delete()

    @classmethod
    def _get_redis_status(cls):
        random_value = generate()
        redis_cache.set("healthpoint_value", random_value)
        retrieved_value = redis_cache.get("healthpoint_value")
        if retrieved_value != random_value:
            return "Could not store and retrieve a value"

        lock = redis_cache.lock("healthpoint_lock", timeout=5)
        try:
            if not lock.acquire(blocking=False):
                return "Could not acquire redis lock"
        finally:
            lock.release()

    @classmethod
    def _get_keycloak_status(cls):
        client = KeycloakUserManager.get_keycloak_client(cache={})
        client.get_users()

    @classmethod
    def _get_smtp_connection_status(cls):
        with mail.get_connection():
            # If the connection doesn't succeed an exception will be thrown.
            pass

    @classmethod
    def _get_bounce_mailbox_status(cls):
        bounce_user = getattr(settings, "EMAIL_BOUNCE_USER", None)
        if not bounce_user:
            return "Missing setting EMAIL_BOUNCE_USER"
        bounce_password = getattr(settings, "EMAIL_BOUNCE_PASSWORD", None)
        if not bounce_password:
            return "Missing setting EMAIL_BOUNCE_PASSWORD"

        mail_client = IMAP4_SSL(settings.EMAIL_HOST, port=settings.EMAIL_PORT_IMAP)
        return_code, _ = mail_client.login(
            settings.EMAIL_BOUNCE_USER, settings.EMAIL_BOUNCE_PASSWORD
        )
        if return_code != "OK":
            return f"Imap server login failed, return code : {return_code}"

        try:
            mail_client.select(readonly=True)
            return_code, _ = mail_client.search(None, "(UNSEEN)")
            if return_code != "OK":
                return f"Imap server search failed, return code : {return_code}"
        finally:
            mail_client.logout()

    @classmethod
    def _get_order_wizard_base_status(cls):
        client = Client()
        response = client.get(reverse("bestell_wizard:bestell_wizard_mobile"))
        if response.status_code != 200:
            return f"Error on order wizard base view, response status code: {response.status_code}"

    @classmethod
    def _get_order_wizard_data_status(cls):
        client = Client()
        response = client.get(reverse("bestell_wizard:bestell_wizard_base_data"))
        if response.status_code != 200:
            return f"Error on order wizard data view, response status code: {response.status_code}"

    @classmethod
    def _get_member_profile_status(cls):
        member = Member.objects.order_by("?").first()
        if member is None:
            return "No member in DB"

        client = Client()
        client.force_login(member)
        response = client.get(reverse("wirgarten:member_detail", args=[member.id]))
        if response.status_code != 200:
            return (
                f"Error on member profile, response status code: {response.status_code}"
            )
