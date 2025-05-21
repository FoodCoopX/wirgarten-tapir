import datetime
from dataclasses import dataclass
from typing import Callable, List, Any, Dict

from django.db.models import QuerySet


@dataclass
class ExportSegmentColumn:
    id: str
    display_name: str
    description: str
    get_value: Callable[[Any, datetime.datetime, Dict], str]


@dataclass
class ExportSegment:
    id: str
    display_name: str
    description: str
    get_queryset: Callable[[datetime.datetime], QuerySet]
    get_available_columns: Callable[[], List[ExportSegmentColumn]]


class ExportSegmentManager:
    registered_export_segments: Dict[str, ExportSegment] = {}

    @classmethod
    def register_segment(cls, segment: ExportSegment):
        cls.registered_export_segments[segment.id] = segment

    @classmethod
    def get_segment_by_id(cls, segment_id: str) -> ExportSegment:
        return cls.registered_export_segments[segment_id]
