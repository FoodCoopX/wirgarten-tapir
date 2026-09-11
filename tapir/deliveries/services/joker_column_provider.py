from __future__ import annotations

import datetime

from tapir.deliveries.models import Joker
from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.utils.services.tapir_cache import TapirCache


class JokerColumnProvider:
    COLUMN_ID_MEMBER_NUMBER = "joker.member_number"
    COLUMN_ID_MEMBER_LAST_NAME = "joker.member_last_name"
    COLUMN_ID_MEMBER_FIRST_NAME = "joker.member_first_name"
    COLUMN_ID_PICKUP_LOCATION = "joker.pickup_location"
    COLUMN_ID_PRODUCT_TYPES = "joker.product_types"
    COLUMN_ID_PRODUCTS = "joker.product"
    COLUMN_ID_CALENDAR_WEEK = "joker.calendar_week"

    @classmethod
    def get_joker_columns(cls):
        return [
            ExportSegmentColumn(
                id=cls.COLUMN_ID_MEMBER_NUMBER,
                display_name="Mitgliedsnummer",
                description="",
                get_value=cls.get_value_member_number,
            ),
            ExportSegmentColumn(
                id=cls.COLUMN_ID_MEMBER_LAST_NAME,
                display_name="Nachname",
                description="",
                get_value=cls.get_value_member_last_name,
            ),
            ExportSegmentColumn(
                id=cls.COLUMN_ID_MEMBER_FIRST_NAME,
                display_name="Vorname",
                description="",
                get_value=cls.get_value_member_first_name,
            ),
            ExportSegmentColumn(
                id=cls.COLUMN_ID_PICKUP_LOCATION,
                display_name="Abholort",
                description="",
                get_value=cls.get_value_pickup_location_name,
            ),
            ExportSegmentColumn(
                id=cls.COLUMN_ID_PRODUCT_TYPES,
                display_name="Produkt-Typen",
                description="",
                get_value=cls.get_value_product_types,
            ),
            ExportSegmentColumn(
                id=cls.COLUMN_ID_PRODUCTS,
                display_name="Produkt",
                description="",
                get_value=cls.get_value_products,
            ),
            ExportSegmentColumn(
                id=cls.COLUMN_ID_CALENDAR_WEEK,
                display_name="KW",
                description="",
                get_value=cls.get_value_calendar_week,
            ),
        ]

    @classmethod
    def get_value_member_number(
        cls, joker: Joker, reference_datetime: datetime.datetime, cache
    ):
        return MemberColumnProvider.get_value_member_number(
            member=joker.member, reference_datetime=reference_datetime, cache=cache
        )

    @classmethod
    def get_value_member_last_name(cls, joker: Joker, _, __):
        return joker.member.last_name

    @classmethod
    def get_value_member_first_name(cls, joker: Joker, _, __):
        return joker.member.first_name

    @classmethod
    def get_value_pickup_location_name(cls, joker: Joker, _, __):
        # This field should be annotated by the segment queryset
        return joker.pickup_location_name

    @classmethod
    def get_value_calendar_week(cls, joker: Joker, _, __):
        # This field should be annotated by the segment queryset
        return str(joker.calendar_week)

    @classmethod
    def get_value_product_types(cls, joker: Joker, _, cache: dict):

        return ",".join(
            [
                subscription.product.type.name
                for subscription in cls.get_relevant_subscriptions(
                    joker=joker, reference_date=joker.date, cache=cache
                )
            ]
        )

    @classmethod
    def get_value_products(cls, joker: Joker, _, cache: dict):

        return ",".join(
            [
                subscription.product.name
                for subscription in cls.get_relevant_subscriptions(
                    joker=joker, reference_date=joker.date, cache=cache
                )
            ]
        )

    @classmethod
    def get_relevant_subscriptions(
        cls, joker: Joker, reference_date: datetime.date, cache: dict
    ):
        member_subscriptions = (
            TapirCache.get_active_and_future_subscriptions_by_member_id(
                reference_date=reference_date, cache=cache
            ).get(joker.member_id, [])
        )
        subscriptions_affected_by_jokers = set(
            TapirCache.get_subscriptions_affected_by_jokers(cache=cache)
        )
        relevant_subscriptions = [
            subscription
            for subscription in member_subscriptions
            if subscription in subscriptions_affected_by_jokers
            and subscription.start_date <= reference_date
            and subscription.end_date >= reference_date
        ]
        return sorted(
            relevant_subscriptions, key=lambda subscription: subscription.product.name
        )
