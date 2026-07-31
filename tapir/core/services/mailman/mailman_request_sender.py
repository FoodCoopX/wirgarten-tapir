import requests
from django.conf import settings
from mailmanclient import Client
from requests import Response

from tapir.utils.shortcuts import get_from_cache_or_compute


class MailmanRequestException(Exception):
    pass


class MailmanRequestSender:
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
        client = MailmanRequestSender.get_client(cache)
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

    @classmethod
    def get(cls, path: str):
        response = requests.get(
            f"http://localhost:8001/3.1/{path}", auth=cls._get_authentication()
        )
        return cls._handle_response(response)

    @classmethod
    def post(cls, path: str, data: dict):
        response = requests.post(
            f"http://localhost:8001/3.1/{path}",
            auth=cls._get_authentication(),
            json=data,
        )
        return cls._handle_response(response)

    @classmethod
    def _handle_response(cls, response: Response):
        response_data = response.json()
        if response.status_code != 200:
            raise MailmanRequestException(
                f"{response_data["title"]: {response_data["description"]}}"
            )

        return response_data

    @staticmethod
    def _get_authentication():
        return settings.MAILMAN_ADMIN_USER, settings.MAILMAN_ADMIN_PASSWORD
