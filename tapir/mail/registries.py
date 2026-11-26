from dataclasses import dataclass
from typing import Callable

from django.db.models import QuerySet

type SegmentQuerysetGetter = Callable[[], QuerySet]
type SegmentQuerysetRegistry = dict[str, SegmentQuerysetGetter]


@dataclass(frozen=True)
class MailSegment:
    get_queryset: SegmentQuerysetGetter
    label: str
    description: str
    group: str


type MailSegmentRegistry = dict[str, MailSegment]
type MailSegmentRegistryProvider = Callable[[], MailSegmentRegistry]

mail_segment_providers = set[MailSegmentRegistryProvider]()


def get_mail_segment_definitions() -> MailSegmentRegistry:
    combined_registry = {}

    for provider in mail_segment_providers:
        combined_registry.update(provider())

    return combined_registry


def get_mail_segments() -> SegmentQuerysetRegistry:
    return {
        segment_name: segment.get_queryset
        for segment_name, segment in get_mail_segment_definitions().items()
    }
