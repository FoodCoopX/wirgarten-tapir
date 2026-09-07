from django.shortcuts import get_object_or_404
from mailmanclient import MailingList

from tapir.core.serializers import (
    MailingListSubscribeInternalRecipientRequestSerializer,
)
from tapir.core.services.mailman.mailing_list_provider import MailingListProvider
from tapir.core.services.mailman.mailing_lists_enabled_checker import (
    MailingListsEnabledChecker,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self


class MailingListSelfRequestPreparer:
    @classmethod
    def prepare(cls, request) -> tuple[MailingList, Member]:
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        serializer = MailingListSubscribeInternalRecipientRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        cache = {}
        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        list_name = serializer.validated_data["list_name"]
        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=list_name, cache=cache
        )
        return mailing_list, member
