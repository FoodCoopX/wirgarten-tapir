from django.http import Http404
from mailmanclient import MailingList
from rest_framework.exceptions import ValidationError

from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.core.services.mailman.mailing_list_serializer_data_builder import (
    MailingListSerializerDataBuilder,
)
from tapir.core.services.mailman.mailing_list_subscription_checker import (
    MailingListSubscriptionChecker,
)
from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient
from tapir.wirgarten.utils import get_now


class MailingListSelfService:
    @classmethod
    def build_list_data(
        cls, email: str, include_advertised_lists: bool, cache: dict
    ) -> dict:
        belongs_to_former_member = FormerMemberAddressProvider.is_former_member_address(
            address=email, reference_datetime=get_now(cache=cache), cache=cache
        )
        include_advertised_lists = (
            include_advertised_lists and not belongs_to_former_member
        )
        relevant_lists = [
            mailing_list
            for mailing_list in TapirMailmanClient.get_domain(cache=cache).lists
            if cls._should_show_list(
                email=email,
                mailing_list=mailing_list,
                include_advertised_lists=include_advertised_lists,
            )
        ]

        return {
            "belongs_to_former_member": belongs_to_former_member,
            "available_lists": [
                MailingListSerializerDataBuilder.build_serializer_data(mailing_list)
                for mailing_list in relevant_lists
            ],
            "subscribed_lists": [
                mailing_list.fqdn_listname
                for mailing_list in relevant_lists
                if MailingListSubscriptionChecker.is_member_subscribed_to_list(
                    email=email, mailing_list=mailing_list
                )
            ],
            "waiting_for_confirmation_lists": [
                mailing_list.fqdn_listname
                for mailing_list in relevant_lists
                if MailingListSubscriptionChecker.is_member_waiting_for_confirmation(
                    email=email, mailing_list=mailing_list
                )
            ],
        }

    @staticmethod
    def subscribe(email: str, mailing_list: MailingList):
        if not mailing_list.settings["advertised"]:
            raise Http404(f"Keine Liste mit Name {mailing_list.listname} gefunden")

        if MailingListSubscriptionChecker.is_member_subscribed_to_list(
            email=email, mailing_list=mailing_list
        ):
            raise ValidationError(
                f"Die Adresse {email} ist schon zu Liste {mailing_list.fqdn_listname} angemeldet"
            )

        mailing_list.subscribe(
            address=email,
            invitation=False,
            pre_confirmed=True,
            pre_verified=True,
        )

    @staticmethod
    def unsubscribe(email: str, mailing_list: MailingList):
        if not MailingListSubscriptionChecker.is_member_subscribed_to_list(
            email=email, mailing_list=mailing_list
        ):
            raise ValidationError(
                f"Die Adresse {email} ist nicht zu {mailing_list.fqdn_listname} angemeldet"
            )

        mailing_list.unsubscribe(email=email, pre_confirmed=True, pre_approved=True)

    @classmethod
    def accept_invitation(cls, email: str, mailing_list: MailingList):
        mailing_list.accept_request(
            request_id=cls._get_invitation_token(email=email, mailing_list=mailing_list)
        )

    @classmethod
    def reject_invitation(cls, email: str, mailing_list: MailingList):
        mailing_list.reject_request(
            request_id=cls._get_invitation_token(email=email, mailing_list=mailing_list)
        )

    @staticmethod
    def _get_invitation_token(email: str, mailing_list: MailingList) -> str:
        for request in mailing_list.requests:
            if request["email"] == email:
                return request["token"]

        raise ValidationError(
            f"Die Adresse {email} ist nicht zu {mailing_list.fqdn_listname} eingeladen"
        )

    @staticmethod
    def _should_show_list(
        email: str, mailing_list: MailingList, include_advertised_lists: bool
    ) -> bool:
        return (
            (include_advertised_lists and mailing_list.settings["advertised"])
            or MailingListSubscriptionChecker.is_member_subscribed_to_list(
                email=email, mailing_list=mailing_list
            )
            or MailingListSubscriptionChecker.is_member_waiting_for_confirmation(
                email=email, mailing_list=mailing_list
            )
        )
