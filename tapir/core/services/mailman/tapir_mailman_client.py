from django.conf import settings
from mailmanclient import Client

from tapir.utils.shortcuts import get_from_cache_or_compute


class MailmanRequestException(Exception):
    pass


class TapirMailmanClient:
    @classmethod
    def get_client(cls, cache: dict) -> Client:
        return get_from_cache_or_compute(
            cache=cache,
            key="mailman_client",
            compute_function=lambda: Client(
                baseurl=settings.MAILMAN_URL,
                name=settings.MAILMAN_ADMIN_USER,
                password=settings.MAILMAN_ADMIN_PASSWORD,
            ),
        )

    @classmethod
    def get_domain(cls, cache: dict):
        client = TapirMailmanClient.get_client(cache)
        return client.get_domain(mail_host=settings.EMAIL_HOST)

    @classmethod
    def ensure_instance_domain_exists(cls, cache: dict):
        client = cls.get_client(cache)
        if any(domain.mail_host == settings.EMAIL_HOST for domain in client.domains):
            return
        client.create_domain(
            mail_host=settings.EMAIL_HOST,
            description=f"The domain for the {settings.SITE_URL} instance",
        )
