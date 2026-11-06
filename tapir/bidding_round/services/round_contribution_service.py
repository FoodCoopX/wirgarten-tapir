import json

from django.core import serializers
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.models import BiddingRoundContributionChange
from tapir.solidarity_contribution.models import (
    SolidarityContribution,
    SolidarityContributionChangedLogEntry,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.utils.shortcuts import get_from_cache_or_compute


class RoundContributionService:
    @classmethod
    @transaction.atomic
    def assign_contribution(
        cls, bidding_round, member, change_date, amount, actor, cache: dict
    ):
        cls._invalidate_cache(member.pk, cache)
        previous = cls._get_state(member.pk, cache)
        contribution_ids = [entry["pk"] for entry in previous]
        log_links = list(
            SolidarityContributionChangedLogEntry.objects.filter(
                Q(old_contribution_id__in=contribution_ids)
                | Q(new_contribution_id__in=contribution_ids)
            ).values("pk", "old_contribution_id", "new_contribution_id")
        )
        result = MemberSolidarityContributionService.assign_contribution_to_member(
            member=member,
            change_date=change_date,
            amount=amount,
            actor=actor,
            cache=cache,
        )
        cls._invalidate_cache(member.pk, cache)
        applied = cls._get_state(member.pk, cache)
        if bidding_round.contribution_changes_tracked and previous != applied:
            change, _ = BiddingRoundContributionChange.objects.get_or_create(
                round=bidding_round,
                member=member,
                defaults={
                    "previous_contributions": previous,
                    "applied_contributions": applied,
                    "previous_log_links": log_links,
                },
            )
            change.applied_contributions = applied
            change.save(update_fields=["applied_contributions"])
        return result

    @classmethod
    def restore_contributions(cls, bidding_round, cache: dict):
        changes = list(
            BiddingRoundContributionChange.objects.filter(round=bidding_round).order_by(
                "member_id"
            )
        )
        for change in changes:
            cls._invalidate_cache(change.member_id, cache)
            if cls._get_state(change.member_id, cache) != change.applied_contributions:
                raise ValidationError(
                    _(
                        "Solidaritätsbeiträge wurden nach der Vertragserzeugung geändert. Bitte die Rücknahme manuell prüfen."
                    )
                )
        for change in changes:
            previous = {entry["pk"]: entry for entry in change.previous_contributions}
            applied = {entry["pk"]: entry for entry in change.applied_contributions}
            SolidarityContribution.objects.filter(
                pk__in=applied.keys() - previous.keys()
            ).delete()
            changed_previous = [
                entry for pk, entry in previous.items() if applied.get(pk) != entry
            ]
            for deserialized in serializers.deserialize(
                "json", json.dumps(changed_previous)
            ):
                deserialized.save()
            for link in change.previous_log_links:
                for field in ["old_contribution_id", "new_contribution_id"]:
                    if link[field] is not None:
                        SolidarityContributionChangedLogEntry.objects.filter(
                            pk=link["pk"], **{field + "__isnull": True}
                        ).update(**{field: link[field]})
            cls._invalidate_cache(change.member_id, cache)
            change.delete()

    @classmethod
    def _get_state(cls, member_id: str, cache: dict):
        return get_from_cache_or_compute(
            cache,
            ("round_contribution_state", member_id),
            lambda: json.loads(
                serializers.serialize(
                    "json",
                    SolidarityContribution.objects.filter(member_id=member_id).order_by(
                        "pk"
                    ),
                )
            ),
        )

    @classmethod
    def _invalidate_cache(cls, member_id: str, cache: dict):
        cache.pop(("round_contribution_state", member_id), None)
        for key in [
            "all_solidarity_contributions",
            "all_solidarity_contributions_by_member_id",
            "solidarity_contributions_by_date",
            "solidarity_contributions_by_member_id",
        ]:
            cache.pop(key, None)
