import io
import re
from datetime import date
from django.utils.translation import gettext_lazy as _

from django.core.exceptions import ValidationError

from tapir.wirgarten.models import GrowingPeriod
from lxml import etree


def validate_growing_period_overlap(start_date: date, end_date: date):
    """
    Validates if the given start and end dates would overlap with and existing GrowingPeriod.

    :param start_date: the start date of the new growing period
    :param end_date: the end date of the new growing period
    """

    query = GrowingPeriod.objects.filter(
        start_date__lte=end_date, end_date__gte=start_date
    )
    if query.exists():
        colliding = query.first()
        raise ValidationError(
            f"{_('The growing periods must not overlap! Colliding period:')} {colliding.start_date} - {colliding.end_date}"
        )


def validate_date_range(start_date: date, end_date: date):
    """
    Validates if the given date range is valid.

    :param start_date: the start of the date range
    :param end_date: the end of a date range
    """

    if start_date > end_date:
        raise ValidationError(
            f"{_('The start date must be before the end date!')} start: {start_date}, end: {end_date}"
        )

    if start_date == end_date:
        raise ValidationError(
            f"{_('The start date must not be the same as the end date!')} start: {start_date}, end: {end_date}"
        )


def validate_html(html: str):
    """
    Validates if the given string is HTML conform and if all tags are closing.

    :param html: the html string
    """

    def find_next_unclosed(text):
        """Finds the next unclosed HTML tag"""
        tag_stack = []
        # Get an iterator of all tags in file.
        tag_regex = re.compile(r"<(/?[^/>]*)>", re.DOTALL)
        tags = tag_regex.finditer(text)
        for tag in tags:
            # If it is a closing tag check if it matches the last opening tag.
            if re.match(r"</([^>]*)>", tag.group()):
                top_tag = tag_stack[-1]
                if top_tag.groups()[0] == tag.groups()[0][1:]:
                    tag_stack.pop()
                else:
                    unclosed = tag_stack.pop()
                    return (unclosed.start(), unclosed.end())
            else:
                tag_stack.append(tag)

        if len(tag_stack) > 0:
            unclosed = tag_stack.pop()
            return (unclosed.start(), unclosed.end())

    try:
        etree.parse(io.StringIO(html), etree.HTMLParser(recover=False))
    except Exception as e:
        raise ValidationError("Invalid HTML! Details: " + str(e))

    position = find_next_unclosed(html)
    if position:
        tag = html[position[0] : position[1]]
        raise ValidationError(f"Unclosed HTML tag {tag} at {position}!")
