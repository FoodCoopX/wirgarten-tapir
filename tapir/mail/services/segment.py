import logging
import traceback

from django.db.models import QuerySet

from tapir.core.services.member_extra_recipient_provider import (
    MemberExtraRecipientProvider,
)
from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.mail.models import StaticSegment, MailCategory
from tapir.mail.registries import get_mail_segments, SegmentQuerysetRegistry
from tapir.mail.services.mail_category_recipients_resolver import (
    MailCategoryRecipientResolver,
)
from tapir.mail.triggers.transactional_trigger import TransactionalTriggerData

LOG = logging.getLogger(__name__)

BASE_QUERYSET: QuerySet | None = None


def _check_base_queryset():
    if BASE_QUERYSET is None:
        raise ValueError(
            "Base queryset not set. Please call register_base_segment first."
        )


def register_base_segment(queryset):
    global BASE_QUERYSET
    BASE_QUERYSET = queryset


def _apply_top_operator(operator_stack, operand_stack):
    if not operator_stack:
        return

    operator = operator_stack.pop()
    if operator == "NOT":
        if operand_stack:
            operand_stack.append(~operand_stack.pop())
        else:
            raise ValueError("Missing operand for NOT")
    else:
        if len(operand_stack) >= 2:
            right = operand_stack.pop()
            left = operand_stack.pop()
            if operator == "AND":
                operand_stack.append(left & right)
            elif operator == "OR":
                operand_stack.append(left | right)
        else:
            raise ValueError("Missing operand for AND/OR")


def resolve_segments(
    cache: dict,
    dynamic_segment_names_additive=None,
    static_segment_ids_additive=None,
    static_segment_ids_subtractive=None,
    dynamic_segment_names_subtractive=None,
    mail_category_ids_additive=None,
    override_recipients: list = None,
) -> list[AddressedRecipient]:
    if dynamic_segment_names_subtractive is None:
        dynamic_segment_names_subtractive = []
    if static_segment_ids_additive is None:
        static_segment_ids_additive = []
    if dynamic_segment_names_additive is None:
        dynamic_segment_names_additive = []
    if static_segment_ids_subtractive is None:
        static_segment_ids_subtractive = []
    if mail_category_ids_additive is None:
        mail_category_ids_additive = []

    if (
        not dynamic_segment_names_additive
        and not static_segment_ids_additive
        and not mail_category_ids_additive
        and not override_recipients
    ):
        raise ValueError("At least one segment should be added.")

    try:
        return __resolve_segments_internal(
            dynamic_segment_names_additive=dynamic_segment_names_additive,
            dynamic_segment_names_subtractive=dynamic_segment_names_subtractive,
            static_segment_ids_additive=static_segment_ids_additive,
            static_segment_ids_subtractive=static_segment_ids_subtractive,
            mail_category_ids_additive=mail_category_ids_additive,
            override_recipients=override_recipients,
            cache=cache,
        )
    except Exception as e:
        LOG.error(
            f"Error combining segments: {e}. addSegments: {dynamic_segment_names_additive}, removeSegments: {dynamic_segment_names_subtractive}, override_recipients: {override_recipients}, mail_categories: {mail_category_ids_additive}"
        )
        traceback.print_exc()
        raise e


def __resolve_segments_internal(
    dynamic_segment_names_additive: list[str],
    dynamic_segment_names_subtractive: list[str],
    static_segment_ids_additive: list[str],
    static_segment_ids_subtractive: list[str],
    mail_category_ids_additive: list[str],
    override_recipients: list | None,
    cache: dict,
) -> list[AddressedRecipient]:
    combined = BASE_QUERYSET.none()

    segment_registry = get_mail_segments()

    combined = add_dynamic_segments(
        queryset=combined,
        segment_names=dynamic_segment_names_additive,
        segment_registry=segment_registry,
    )
    combined = remove_dynamic_segments(
        queryset=combined,
        segment_names=dynamic_segment_names_subtractive,
        segment_registry=segment_registry,
    )

    ids = combined.values_list("id", flat=True)
    combined = BASE_QUERYSET.filter(id__in=ids).distinct()

    result = []
    for member in combined:
        result.append(AddressedRecipient.at_own_address(member))
        result.extend(
            MemberExtraRecipientProvider.get_direct_mail_recipients(
                member=member, cache=cache
            )
        )

    add_mail_categories(
        recipient_list=result,
        mail_category_ids=mail_category_ids_additive,
        cache=cache,
    )
    add_static_segments(recipient_list=result, segment_ids=static_segment_ids_additive)

    result = remove_static_segments(
        recipient_list=result, segment_ids=static_segment_ids_subtractive
    )

    if override_recipients:
        result = apply_recipient_override(result, override_recipients)

    return deduplicate_by_email(result)


def deduplicate_by_email(
    recipient_list: list[AddressedRecipient],
) -> list[AddressedRecipient]:
    recipients_by_email = {}
    for addressed_recipient in recipient_list:
        recipients_by_email.setdefault(addressed_recipient.email, addressed_recipient)
    return list(recipients_by_email.values())


def remove_static_segments(
    recipient_list: list[AddressedRecipient], segment_ids: list[str]
) -> list[AddressedRecipient]:
    email_addresses_to_remove = set()
    for static_segment_subtractive in StaticSegment.objects.filter(id__in=segment_ids):
        email_addresses_to_remove.update(
            static_segment_subtractive.recipients.values_list("email", flat=True)
        )

    return [
        addressed_recipient
        for addressed_recipient in recipient_list
        if addressed_recipient.email not in email_addresses_to_remove
    ]


def add_static_segments(
    recipient_list: list[AddressedRecipient], segment_ids: list[str]
):
    for segment in StaticSegment.objects.filter(id__in=segment_ids):
        LOG.info(f"Adding static segment {segment.name}")
        recipient_list.extend(
            AddressedRecipient.at_own_address(recipient)
            for recipient in segment.recipients.all()
        )


def add_mail_categories(
    recipient_list: list[AddressedRecipient],
    mail_category_ids: list[str],
    cache: dict,
):
    for mail_category_id in mail_category_ids:
        mail_category = MailCategory.objects.get(id=mail_category_id)
        recipient_list.extend(
            MailCategoryRecipientResolver.resolve_recipients(
                mail_category=mail_category, cache=cache
            )
        )


def add_dynamic_segments(
    queryset: QuerySet,
    segment_names: list[str],
    segment_registry: SegmentQuerysetRegistry,
):
    for segment_name in segment_names:
        LOG.info(f"Adding segment {segment_name}")
        queryset = queryset.union(segment_registry[segment_name]())
    return queryset


def remove_dynamic_segments(
    queryset: QuerySet,
    segment_names: list[str],
    segment_registry: SegmentQuerysetRegistry,
):
    for segment_name in segment_names:
        LOG.info(f"Subtracting segment {segment_name}")
        queryset = queryset.difference(segment_registry[segment_name]())
    return queryset


def apply_recipient_override(
    recipients: list[AddressedRecipient], overrides: list[dict]
) -> list[AddressedRecipient]:
    updated_recipients = []
    for override in overrides:
        recipient_outside_of_base_queryset = override.get(
            "recipient_outside_of_base_queryset", None
        )
        if recipient_outside_of_base_queryset is not None:
            return [
                AddressedRecipient.at_own_address(
                    TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                        **recipient_outside_of_base_queryset
                    )
                )
            ]

        recipient_id_in_base_queryset = override.get(
            "recipient_id_in_base_queryset", None
        )
        updated_recipients.extend(
            addressed_recipient
            for addressed_recipient in recipients
            if getattr(addressed_recipient.recipient, "id", None)
            == recipient_id_in_base_queryset
        )

    return updated_recipients
