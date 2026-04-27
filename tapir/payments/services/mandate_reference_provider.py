import datetime

import nanoid
from django.core.exceptions import ImproperlyConfigured
from unidecode import unidecode

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.mandate_reference_pattern_validator import (
    MandateReferencePatternValidator,
)
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import Member, MandateReference
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_now


class MandateReferenceProvider:

    @classmethod
    def get_or_create_mandate_reference(
        cls, member: Member, cache: dict, reference_datetime: datetime.datetime = None
    ):
        if reference_datetime is None:
            reference_datetime = get_now(cache=cache)

        def compute() -> dict[str, list[MandateReference]]:
            new_cache = dict.fromkeys(Member.objects.values_list("id", flat=True), [])
            for mandate_reference in MandateReference.objects.select_related(
                "member"
            ).order_by("-start_ts"):
                new_cache[mandate_reference.member_id].append(mandate_reference)
            return new_cache

        mandate_ref_cache = get_from_cache_or_compute(
            cache, "mandate_ref_cache", compute
        )
        mandate_refs = mandate_ref_cache.get(member.id)
        for mandate_ref in mandate_refs:
            if mandate_ref.start_ts <= reference_datetime:
                return mandate_ref

        if len(mandate_refs) > 0:
            # If a mandate reference already exists, we should use it even if it's validity starts after the reference_datetime
            return mandate_refs[0]

        mandate_ref = cls._create_mandate_ref(member=member, cache=cache)
        if mandate_ref_cache is not None:
            mandate_ref_cache[member.id].append(mandate_ref)

        return mandate_ref

    @classmethod
    def _create_mandate_ref(cls, member: Member, cache: dict):
        ref = cls.build_mandate_ref(
            member=member,
            pattern=get_parameter_value(
                key=ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN, cache=cache
            ),
        )
        return MandateReference.objects.create(
            ref=ref, member=member, start_ts=get_now(cache=cache)
        )

    @classmethod
    def build_mandate_ref(cls, member: Member, pattern: str):
        if member.member_no is None:
            cls._validate_member_number_is_not_required(member=member, pattern=pattern)

        for token in [
            MandateReferencePatternValidator.TOKEN_MEMBER_NUMBER_LONG,
            MandateReferencePatternValidator.TOKEN_MEMBER_NUMBER_WITHOUT_PREFIX,
        ]:
            if token in pattern:
                raise NotImplementedError("Waiting for US 4.3, PR #1084")

        pattern = pattern.replace(
            MandateReferencePatternValidator.get_token_with_braces(
                MandateReferencePatternValidator.TOKEN_FIRST_NAME
            ),
            unidecode(member.first_name[:5]),
        )
        pattern = pattern.replace(
            MandateReferencePatternValidator.get_token_with_braces(
                MandateReferencePatternValidator.TOKEN_LAST_NAME
            ),
            unidecode(member.last_name[:5]),
        )
        pattern = pattern.replace(
            MandateReferencePatternValidator.get_token_with_braces(
                MandateReferencePatternValidator.TOKEN_MEMBER_NUMBER_SHORT
            ),
            str(member.member_no),
        )

        target_length = MandateReferencePatternValidator.MANDATE_REF_LENGTH - len(
            pattern.replace(
                MandateReferencePatternValidator.get_token_with_braces(
                    MandateReferencePatternValidator.TOKEN_RANDOM
                ),
                "",
            )
        )
        pattern = pattern.replace(
            "{zufall}",
            nanoid.generate(
                MandateReferencePatternValidator.RANDOM_TOKEN_ALPHABET, target_length
            ),
        )

        return pattern.upper()

    @classmethod
    def _validate_member_number_is_not_required(cls, pattern: str, member: Member):
        for (
            token
        ) in MandateReferencePatternValidator.TOKENS_THAT_REQUIRE_A_MEMBER_NUMBER:
            if MandateReferencePatternValidator.get_token_with_braces(token) in pattern:
                raise ImproperlyConfigured(
                    f"The pattern for mandate references is {pattern}, which uses a member number, but the given member does not have a member number: {member}"
                )
