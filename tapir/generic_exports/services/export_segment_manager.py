import datetime
from dataclasses import dataclass
from typing import Callable, List, Any, Iterable


@dataclass
class ExportSegmentColumn:
    id: str
    display_name: str
    description: str
    get_value: Callable[[Any, datetime.datetime, dict], Any]


@dataclass
class ExportSegment:
    id: str
    display_name: str
    get_queryset: Callable[[datetime.datetime], Iterable]
    get_available_columns: Callable[[], List[ExportSegmentColumn]]
    # Set exactly one of description and get_description
    description: str = ""
    get_description: Callable[[dict], str] | None = None


class ExportSegmentManager:
    registered_export_segments: dict[str, ExportSegment] = {}

    @classmethod
    def register_segment(cls, segment: ExportSegment):
        cls.registered_export_segments[segment.id] = segment

    @classmethod
    def get_segment_by_id(cls, segment_id: str) -> ExportSegment:
        return cls.registered_export_segments[segment_id]
