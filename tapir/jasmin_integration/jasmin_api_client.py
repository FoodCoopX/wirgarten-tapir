import json

from core.errors import JasminError
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, RestrictedError
from rest_framework.test import APIRequestFactory, force_authenticate

from tapir.jasmin_integration.exceptions import JasminSynchronisationException


class JasminApiClient:
    """Writes to Jasmin through its own API views, in-process and as the given user.

    Jasmin's validation, permission checks and side effects (for example the default
    share contents of a new station day, or the succession of delivery days) run
    exactly as when the office uses Jasmin's interface. Reads can still go to the
    models directly."""

    def __init__(self, user):
        self.user = user
        self.request_factory = APIRequestFactory()

    def create(self, viewset_class, data: dict) -> dict:
        return self._call(viewset_class, action="create", method="post", data=data)

    def update(self, viewset_class, pk: str, data: dict) -> dict:
        return self._call(
            viewset_class, action="partial_update", method="patch", data=data, pk=pk
        )

    def destroy(self, viewset_class, pk: str) -> None:
        self._call(viewset_class, action="destroy", method="delete", pk=pk)

    def _call(
        self,
        viewset_class,
        action: str,
        method: str,
        data: dict | None = None,
        pk: str | None = None,
    ) -> dict:
        request = getattr(self.request_factory, method)("/", data=data, format="json")
        force_authenticate(request, user=self.user)
        view = viewset_class.as_view({method: action})
        description = f"{viewset_class.__name__}.{action}"

        try:
            # A savepoint per call: a refused call must not break the surrounding
            # transaction.
            with transaction.atomic():
                response = view(request, **({} if pk is None else {"pk": pk}))
                if response.status_code >= 400:
                    raise JasminSynchronisationException(
                        self.build_error_message(
                            description, json.dumps(response.data, default=str)
                        )
                    )
        except JasminError as error:
            raise JasminSynchronisationException(
                self.build_error_message(description, error.message)
            ) from error
        except (
            ValidationError,
            ProtectedError,
            RestrictedError,
            IntegrityError,
        ) as error:
            raise JasminSynchronisationException(
                self.build_error_message(description, str(error))
            ) from error

        return response.data

    @staticmethod
    def build_error_message(description: str, details: str) -> str:
        return f"Jasmin hat folgende Änderung abgelehnt ({description}): {details}"
