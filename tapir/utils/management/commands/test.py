import traceback
from typing import Iterable

from django.core.management import BaseCommand
from icecream import ic
from tapir_mail.models import EmailConfigurationDispatch
from tapir_mail.service.segment import (
    BASE_QUERYSET,
    LOG,
    segment_registry,
    _apply_complex_filters,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        ecd = EmailConfigurationDispatch.objects.first()
        resolve_segments(
            **ecd.email_configuration_version.segment_data,
            override_recipients=ecd.override_recipients,
        )


def resolve_segments(
    add_segments=None,
    static_segments=None,
    static_segments_subtractive=None,
    remove_segments=None,
    filter_list=None,
    override_recipients: list[str | tuple[str, str]] = None,
) -> list:
    if filter_list is None:
        filter_list = []
    if remove_segments is None:
        remove_segments = []
    if static_segments is None:
        static_segments = []
    if add_segments is None:
        add_segments = []
    if static_segments_subtractive is None:
        static_segments_subtractive = []

    from tapir_mail.models import StaticSegment

    if not add_segments and not static_segments:
        raise ValueError("At least one segment should be added.")

    try:
        combined = BASE_QUERYSET.none()

        # Combine segments using union
        for segment in add_segments:
            LOG.info(f"Adding segment {segment}")
            combined = combined.union(segment_registry[segment]())

        # Subtract segments using difference
        for segment in remove_segments:
            LOG.info(f"Subtracting segment {segment}")
            combined = combined.difference(segment_registry[segment]())

        # Apply complex filters
        if filter_list:
            LOG.info(f"Adding filters {filter_list}")
            id_list = list(combined.values_list("id", flat=True))
            combined = _apply_complex_filters(
                BASE_QUERYSET.filter(id__in=id_list), filter_list
            )

        # Can't call distinct() right away because we called difference() before on combined
        ids = combined.values_list("id", flat=True)
        combined = BASE_QUERYSET.filter(id__in=ids).distinct()

        result = list(combined)

        # Add static segments
        static_segments = StaticSegment.objects.filter(name__in=static_segments)
        for segment in static_segments:
            LOG.info(f"Adding static segment {segment.name}")
            result.extend(segment.recipients.all())

        recipients_subtractive = []
        for static_segment_subtractive in StaticSegment.objects.filter(
            name__in=static_segments_subtractive
        ):
            recipients_subtractive.extend(
                static_segment_subtractive.recipients.values_list("email", flat=True)
            )

        result = [
            recipient
            for recipient in result
            if recipient.email not in recipients_subtractive
        ]

        if override_recipients:
            result = apply_recipient_override(result, override_recipients)

        return result
    except Exception as e:
        LOG.error(
            f"Error combining segments: {e}. addSegments: {add_segments}, removeSegments: {remove_segments}, filterList: {filter_list}, override_recipients: {override_recipients}"
        )
        traceback.print_exc()
        raise e


def apply_recipient_override(
    recipients: list, override: list[str | tuple[str, str]]
) -> list:
    override_map = {}
    for data in override:
        if isinstance(data, Iterable) and not isinstance(data, str):
            email_source = data[0]
            email_target = data[1]
        else:
            ic("NOGO")
            email_source = data
            email_target = data
        ic(override, data, email_source, email_target)
        override_map[email_source] = email_target

    result = [
        recipient for recipient in recipients if recipient.email in override_map.keys()
    ]
    for recipient in result:
        recipient.email = override_map[recipient.email]

    return result
