from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn

if TYPE_CHECKING:
    from tapir.wirgarten.models import Member


class MemberColumnProvider:
    @classmethod
    def get_member_columns(cls):
        return [
            ExportSegmentColumn(
                id="member_first_name",
                display_name="Vorname",
                description="",
                get_value=cls.get_value_member_first_name,
            ),
            ExportSegmentColumn(
                id="member_last_name",
                display_name="Nachname",
                description="",
                get_value=cls.get_value_member_last_name,
            ),
            ExportSegmentColumn(
                id="member_number",
                display_name="Mitgliedsnummer",
                description="",
                get_value=cls.get_value_member_number,
            ),
            ExportSegmentColumn(
                id="member_subscriptions",
                display_name="Produkte",
                description="",
                get_value=cls.get_value_member_subscriptions,
            ),
        ]

    @classmethod
    def get_value_member_first_name(cls, member: Member, _):
        return member.first_name

    @classmethod
    def get_value_member_last_name(cls, member: Member, _):
        return member.last_name

    @classmethod
    def get_value_member_number(cls, member: Member, _):
        return str(member.member_no)

    @classmethod
    def get_value_member_subscriptions(
        cls, member: Member, reference_datetime: datetime.datetime
    ):
        from tapir.wirgarten.service.products import get_active_subscriptions

        subscriptions_as_string = [
            f"{subscription.quantity} × {subscription.product.name} {subscription.product.type.name}"
            for subscription in get_active_subscriptions(
                reference_datetime.date()
            ).filter(member=member)
        ]

        return " - ".join(subscriptions_as_string)
