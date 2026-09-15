from __future__ import annotations

from django.db.models import QuerySet, Value
from django.db.models.functions import Lower, Replace

GERMAN_SORT_REPLACEMENTS = (
    ("ä", "ae"),
    ("ö", "oe"),
    ("ü", "ue"),
    ("ß", "ss"),
)


class GermanNameSortService:
    @classmethod
    def annotate_queryset_with_sort_keys(
        cls, queryset: QuerySet, field_names: list[str], cache: dict
    ) -> QuerySet:
        annotations = {
            cls.build_sort_key_annotation_name(
                field_name
            ): cls.build_sort_key_expression(field_name)
            for field_name in field_names
        }
        return queryset.annotate(**annotations)

    @classmethod
    def build_sort_key_annotation_name(cls, field_name: str) -> str:
        return f"{field_name.replace('__', '_')}_sort_key"

    @classmethod
    def build_sort_key_expression(cls, field_name: str) -> Replace:
        expression = Lower(field_name)
        for umlaut, replacement in GERMAN_SORT_REPLACEMENTS:
            expression = Replace(expression, Value(umlaut), Value(replacement))
        return expression
