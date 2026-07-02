from __future__ import annotations

import operator
from functools import reduce

from django.db.models import CharField, Q, QuerySet, Value
from django.db.models.functions import Cast, Concat, LPad

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class MemberSearchService:
    """
    Free-text search for the member list filter.

    Mirrors the Verträge member dropdown (Selectize on Member.__str__): each
    whitespace-separated token must match somewhere on the member (AND across
    tokens, OR across fields per token). Member numbers are matched by substring
    on the raw integer, zero-padded number, and formatted number (prefix + padding)
    as shown in the UI, e.g. BT0118 or 011.
    """

    @classmethod
    def filter_queryset(
        cls, queryset: QuerySet, search_value: str, cache: dict
    ) -> QuerySet:
        if not search_value:
            return queryset

        search_value = search_value.strip()
        if not search_value:
            return queryset

        tokens = search_value.split()
        queryset = cls.annotate_queryset_for_search(queryset, cache=cache)

        # AND across tokens so "Max Mustermann" matches first_name + last_name.
        for token in tokens:
            queryset = queryset.filter(cls.build_token_query(token))

        return queryset

    @classmethod
    def annotate_queryset_for_search(cls, queryset: QuerySet, cache: dict) -> QuerySet:
        prefix = get_parameter_value(ParameterKeys.MEMBER_NUMBER_PREFIX, cache=cache)
        pad_length = get_parameter_value(
            ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, cache=cache
        )

        member_no_text = Cast("member_no", CharField())
        if pad_length > 0:
            padded_member_no_text = LPad(
                member_no_text, pad_length, Value("0"), output_field=CharField()
            )
        else:
            padded_member_no_text = member_no_text

        return queryset.annotate(
            # first_name and last_name are separate columns; Concat enables full-name search.
            full_name=Concat("first_name", Value(" "), "last_name"),
            # member_no is an integer; Cast enables icontains substring search (e.g. "12" in 1234).
            member_no_text=member_no_text,
            # Padded and formatted strings match how member numbers appear in the UI (e.g. 011 in 0118).
            padded_member_no_text=padded_member_no_text,
            formatted_member_no_text=Concat(
                Value(prefix), padded_member_no_text, output_field=CharField()
            ),
        )

    @classmethod
    def build_token_query(cls, token: str) -> Q:
        return reduce(
            operator.or_,
            [
                Q(first_name__icontains=token),
                Q(last_name__icontains=token),
                Q(email__icontains=token),
                Q(full_name__icontains=token),
                Q(member_no_text__icontains=token),
                Q(padded_member_no_text__icontains=token),
                Q(formatted_member_no_text__icontains=token),
            ],
        )
