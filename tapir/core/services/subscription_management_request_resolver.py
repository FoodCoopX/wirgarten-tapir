from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.mail.models import ExternalRecipient, MailCategory
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.parameter_keys import ParameterKeys


class SubscriptionManagementRequestResolver:
    INVALID_TOKEN_MESSAGE = "Dieser Link ist abgelaufen oder ungültig."
    FEATURE_DISABLED_MESSAGE = "Diese Funktion ist ausgeschaltet."

    @classmethod
    def get_address(cls, token: str | None, cache: dict) -> str:
        address = SubscriptionManagementTokenSigner.get_address(token=token or "")
        if address is None or TapirCache.is_member_main_address(
            address=address, cache=cache
        ):
            raise PermissionDenied(cls.INVALID_TOKEN_MESSAGE)
        return address

    @classmethod
    def get_extra_email(cls, address: str, cache: dict) -> MemberExtraEmail:
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ):
            raise ValidationError(cls.FEATURE_DISABLED_MESSAGE)
        return get_object_or_404(
            MemberExtraEmail.objects.select_related("member"),
            email=address,
            confirmed_on__isnull=False,
        )

    @staticmethod
    def can_subscribe_to_lists(address: str, cache: dict) -> bool:
        if ExternalRecipient.objects.filter(email=address).exists():
            return True

        return (
            get_parameter_value(
                key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
            )
            and MemberExtraEmail.objects.filter(
                email=address, confirmed_on__isnull=False
            ).exists()
        )

    @staticmethod
    def get_external_categories() -> list[MailCategory]:
        return list(
            MailCategory.objects.filter(
                available_for_external_recipients=True
            ).order_by("name")
        )
