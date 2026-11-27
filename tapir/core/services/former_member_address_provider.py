import datetime

from tapir.core.services.active_member_provider import ActiveMemberProvider
from tapir.mail.models import ExternalRecipient
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import Member, MemberExtraEmail


class FormerMemberAddressProvider:
    @classmethod
    def get_former_member_by_address(
        cls, reference_datetime: datetime.datetime, cache: dict
    ) -> dict[str, Member]:
        return get_from_cache_or_compute(
            cache,
            f"former_member_by_address_{reference_datetime.date()}",
            lambda: cls._compute_former_member_by_address(
                reference_datetime=reference_datetime, cache=cache
            ),
        )

    @classmethod
    def is_former_member_address(
        cls, address: str, reference_datetime: datetime.datetime, cache: dict
    ) -> bool:
        return address in cls.get_former_member_by_address(
            reference_datetime=reference_datetime, cache=cache
        )

    @staticmethod
    def _compute_former_member_by_address(
        reference_datetime: datetime.datetime, cache: dict
    ) -> dict[str, Member]:
        active_member_ids = set(
            ActiveMemberProvider.get_active_members(
                reference_datetime=reference_datetime, cache=cache
            ).values_list("id", flat=True)
        )
        # Addresses that still belong to someone else keep their lists.
        addresses_in_use = (
            set(
                Member.objects.filter(id__in=active_member_ids).values_list(
                    "email", flat=True
                )
            )
            | set(
                MemberExtraEmail.objects.filter(
                    member_id__in=active_member_ids, confirmed_on__isnull=False
                ).values_list("email", flat=True)
            )
            | set(ExternalRecipient.objects.values_list("email", flat=True))
        )

        former_member_by_address = {
            member.email: member
            for member in Member.objects.exclude(id__in=active_member_ids)
        }
        for extra_email in (
            MemberExtraEmail.objects.exclude(member_id__in=active_member_ids)
            .filter(confirmed_on__isnull=False)
            .select_related("member")
        ):
            former_member_by_address.setdefault(extra_email.email, extra_email.member)

        return {
            address: member
            for address, member in former_member_by_address.items()
            if address not in addresses_in_use
        }
