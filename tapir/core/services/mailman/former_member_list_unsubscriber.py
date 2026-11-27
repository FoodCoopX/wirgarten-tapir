from django.conf import settings

from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient
from tapir.wirgarten.models import Member, MemberUnsubscribedFromMailingListsLogEntry
from tapir.wirgarten.utils import get_now


class FormerMemberListUnsubscriber:
    @staticmethod
    def unsubscribe_former_members(cache: dict):
        if not settings.MAILING_LISTS_ENABLED:
            return

        former_member_by_address = (
            FormerMemberAddressProvider.get_former_member_by_address(
                reference_datetime=get_now(cache=cache), cache=cache
            )
        )
        removals_by_member: dict[Member, list[str]] = {}
        try:
            for mailing_list in TapirMailmanClient.get_domain(cache=cache).lists:
                for subscriber in mailing_list.members:
                    address = str(subscriber.address)
                    if address not in former_member_by_address:
                        continue
                    mailing_list.unsubscribe(
                        email=address, pre_confirmed=True, pre_approved=True
                    )
                    removals_by_member.setdefault(
                        former_member_by_address[address], []
                    ).append(f"{address}: von {mailing_list.fqdn_listname} abgemeldet")
                for request in mailing_list.requests:
                    address = request["email"]
                    if address not in former_member_by_address:
                        continue
                    mailing_list.discard_request(request_id=request["token"])
                    removals_by_member.setdefault(
                        former_member_by_address[address], []
                    ).append(
                        f"{address}: Anfrage für {mailing_list.fqdn_listname} verworfen"
                    )
        finally:
            for member, removals in removals_by_member.items():
                MemberUnsubscribedFromMailingListsLogEntry().populate_removals(
                    removals=removals, user=member
                ).save()
