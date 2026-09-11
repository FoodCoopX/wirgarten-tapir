from __future__ import annotations

from django.db.models import Case, CharField, F, Q, QuerySet, Value, When
from django.db.models.functions import Cast, Concat, Length, LPad

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class MemberSearchService:
    @classmethod
    def filter_queryset(
        cls, queryset: QuerySet, search_value: str | None, cache: dict
    ) -> QuerySet:
        if not search_value or not search_value.strip():
            return queryset

        search_value = search_value.strip()
        tokens = search_value.split()
        queryset = cls.annotate_queryset_for_search(queryset, cache=cache)

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
        queryset = queryset.annotate(
            member_no_text=member_no_text,
            member_no_len=Length(member_no_text),
        )

        if pad_length > 0:
            padded_member_no_text = Case(
                When(
                    member_no_len__lte=pad_length,
                    then=LPad(
                        F("member_no_text"),
                        pad_length,
                        Value("0"),
                        output_field=CharField(),
                    ),
                ),
                default=F("member_no_text"),
                output_field=CharField(),
            )
        else:
            padded_member_no_text = F("member_no_text")

        return queryset.annotate(
            # first_name and last_name are separate columns; Concat enables full-name search.
            full_name=Concat("first_name", Value(" "), "last_name"),
            # member_no is an integer; Cast enables icontains substring search (e.g. "12" in 1234).
            padded_member_no_text=padded_member_no_text,
            # Padded and formatted strings match how member numbers appear in the UI (e.g. 011 in 0118).
            formatted_member_no_text=Concat(
                Value(prefix), padded_member_no_text, output_field=CharField()
            ),
        )

    @classmethod
    def build_token_query(cls, token: str) -> Q:
        return (
            Q(first_name__icontains=token)
            | Q(last_name__icontains=token)
            | Q(email__icontains=token)
            | Q(full_name__icontains=token)
            | Q(member_no_text__icontains=token)
            | Q(padded_member_no_text__icontains=token)
            | Q(formatted_member_no_text__icontains=token)
        )
