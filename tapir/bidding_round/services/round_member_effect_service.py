import json
from contextlib import contextmanager
from dataclasses import dataclass

from django.core import serializers
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from tapir.bidding_round.models import (
    BiddingRound,
    BiddingRoundCreatedSubscription,
    BiddingRoundMemberEffect,
    BiddingRoundMemberRollbackLogEntry,
)
from tapir.solidarity_contribution.models import (
    SolidarityContribution,
    SolidarityContributionChangedLogEntry,
)
from tapir.wirgarten.models import MandateReference, Subscription
from tapir.wirgarten.utils import get_now


class RoundRollbackError(Exception):
    """Base class for refusals of a member rollback."""


class UntrackedRoundError(RoundRollbackError):
    pass


class NoEffectsError(RoundRollbackError):
    pass


class MemberRollbackConflict(RoundRollbackError):
    def __init__(self, conflicts):
        super().__init__("Der Rollback steht im Konflikt mit dem aktuellen Stand.")
        self.conflicts = conflicts


@dataclass
class TrackedEffect:
    effect: BiddingRoundMemberEffect
    changed: bool = False


class RoundMemberEffectService:
    """Snapshots what a round changes for one member and records it as an effect.

    Every write a round performs for a member runs inside :meth:`track`. The
    context manager freezes the member's subscriptions and solidarity
    contributions before the mutation and stores them next to the resulting
    state. A no-op block leaves no effect behind.
    """

    @classmethod
    def applied_effect(cls, bidding_round, member):
        return BiddingRoundMemberEffect.objects.filter(
            round=bidding_round,
            member=member,
            state=BiddingRoundMemberEffect.State.APPLIED,
        ).first()

    @classmethod
    def has_applied_effects(cls, bidding_round) -> bool:
        return BiddingRoundMemberEffect.objects.filter(
            round=bidding_round, state=BiddingRoundMemberEffect.State.APPLIED
        ).exists()

    @classmethod
    def current_state(cls, effect) -> tuple[list, list]:
        return (
            cls.subscriptions_state(effect.member, effect.round.growing_period),
            cls.contributions_state(effect.member),
        )

    @classmethod
    def subscriptions_state(cls, member, period) -> list:
        return cls._serialize(Subscription.objects.filter(member=member, period=period))

    @classmethod
    def contributions_state(cls, member) -> list:
        return cls._serialize(SolidarityContribution.objects.filter(member=member))

    @classmethod
    def contribution_log_links(cls, contributions: list) -> list:
        contribution_ids = [entry["pk"] for entry in contributions]
        return list(
            SolidarityContributionChangedLogEntry.objects.filter(
                Q(old_contribution_id__in=contribution_ids)
                | Q(new_contribution_id__in=contribution_ids)
            )
            .order_by("pk")
            .values("pk", "old_contribution_id", "new_contribution_id")
        )

    @classmethod
    def mandate_ref_ids(cls, member) -> list:
        return list(
            MandateReference.objects.filter(member=member)
            .order_by("pk")
            .values_list("pk", flat=True)
        )

    @classmethod
    @contextmanager
    def track(
        cls,
        bidding_round,
        member,
        source,
        actor,
        cache,
        always_record=False,
    ):
        """Snapshot, run the mutation, record the effect.

        Yields a :class:`TrackedEffect`. ``changed`` is false when the block left
        every snapshot identical; in that case no effect is written and the
        caller should treat the member as untouched. ``always_record`` records
        the effect even without a row change, which is needed when the mutation
        only writes links.
        """
        with transaction.atomic():
            locked_round = BiddingRound.objects.select_for_update().get(
                pk=bidding_round.pk
            )
            effect = (
                BiddingRoundMemberEffect.objects.select_for_update()
                .filter(round=locked_round, member=member)
                .first()
            )

            keep_previous = (
                effect is not None
                and effect.state == BiddingRoundMemberEffect.State.APPLIED
            )
            if keep_previous:
                previous_subscriptions = effect.previous_subscriptions
                previous_contributions = effect.previous_contributions
                contribution_log_links = effect.contribution_log_links
                previous_mandate_ref_ids = effect.previous_mandate_ref_ids
            else:
                previous_subscriptions = cls.subscriptions_state(
                    member, locked_round.growing_period
                )
                previous_contributions = cls.contributions_state(member)
                contribution_log_links = cls.contribution_log_links(
                    previous_contributions
                )
                previous_mandate_ref_ids = cls.mandate_ref_ids(member)

            if effect is None:
                effect = BiddingRoundMemberEffect(round=locked_round, member=member)

            tracked = TrackedEffect(effect=effect)
            yield tracked

            applied_subscriptions = cls.subscriptions_state(
                member, locked_round.growing_period
            )
            applied_contributions = cls.contributions_state(member)
            created_mandate_ref_ids = sorted(
                set(cls.mandate_ref_ids(member)) - set(previous_mandate_ref_ids)
            )

            tracked.changed = always_record or (
                previous_subscriptions != applied_subscriptions
                or previous_contributions != applied_contributions
            )
            if not tracked.changed:
                return

            if not keep_previous:
                effect.source = source
                effect.reversed_at = None
                effect.reversed_by = None
                effect.reversal_reason = ""
                effect.divergence_overridden = False
            effect.state = BiddingRoundMemberEffect.State.APPLIED
            effect.previous_subscriptions = previous_subscriptions
            effect.applied_subscriptions = applied_subscriptions
            effect.previous_contributions = previous_contributions
            effect.applied_contributions = applied_contributions
            effect.contribution_log_links = contribution_log_links
            effect.previous_mandate_ref_ids = previous_mandate_ref_ids
            effect.created_mandate_ref_ids = created_mandate_ref_ids
            effect.applied_at = get_now(cache=cache)
            effect.save()

    @classmethod
    def _serialize(cls, queryset) -> list:
        return json.loads(serializers.serialize("json", queryset.order_by("pk")))

    @classmethod
    def revert_member(
        cls, bidding_round, member, actor, reason="", force=False, *, cache: dict
    ):
        return cls.revert_members(
            bidding_round,
            [member.id],
            actor=actor,
            reason=reason,
            force=force,
            cache=cache,
        )[0]

    @classmethod
    def revert_members(
        cls,
        bidding_round,
        member_ids,
        actor,
        reason="",
        force=False,
        *,
        cache: dict,
    ) -> list[dict]:
        if force and not reason.strip():
            raise ValidationError(
                "Für eine erzwungene Rücknahme ist eine Begründung erforderlich."
            )
        selected_member_ids = cls._selected_member_ids(member_ids)

        with transaction.atomic():
            locked_round = BiddingRound.objects.select_for_update().get(
                pk=bidding_round.pk
            )
            applied, skipped = cls._load_applied_effects(
                locked_round, selected_member_ids
            )
            if not applied:
                return skipped

            conflicts, diverged_effect_ids = cls._collect_rollback_conflicts(
                applied, locked_round
            )
            if conflicts:
                has_cross_round = any(
                    conflict["kind"] == "cross_round" for conflict in conflicts
                )
                if has_cross_round or not force:
                    raise MemberRollbackConflict(conflicts)

            results = [
                cls._revert_effect(
                    effect,
                    actor=actor,
                    reason=reason,
                    force=force,
                    diverged=effect.pk in diverged_effect_ids,
                    cache=cache,
                )
                for effect in applied
            ]
            results.extend(skipped)
            cls._clear_contracts_created_at(locked_round)

        return results

    @staticmethod
    def _selected_member_ids(member_ids):
        if member_ids is None:
            return None
        return {str(member_id) for member_id in member_ids}

    @classmethod
    def _load_applied_effects(cls, locked_round, selected_member_ids):
        filter_args = (
            {"member_id__in": selected_member_ids}
            if selected_member_ids is not None
            else {}
        )
        effects = list(
            locked_round.member_effects.select_related("member")
            .filter(**filter_args)
            .order_by("member_id")
        )
        if not effects:
            if locked_round.contracts_created_at is not None:
                raise UntrackedRoundError(
                    "Für diese Runde fehlt der aufgezeichnete Vorzustand. "
                    "Bitte die Rücknahme manuell prüfen."
                )
            raise NoEffectsError(
                "Für diese Runde gibt es keine Verträge zum Zurücknehmen."
            )

        applied = [
            effect
            for effect in effects
            if effect.state == BiddingRoundMemberEffect.State.APPLIED
        ]
        skipped = [
            cls._result(effect, state="skipped")
            for effect in effects
            if effect.state != BiddingRoundMemberEffect.State.APPLIED
        ]
        return applied, skipped

    @classmethod
    def _collect_rollback_conflicts(cls, applied, locked_round):
        conflicts = []
        diverged_effect_ids = set()
        for effect in applied:
            conflicts.extend(cls._cross_round_conflicts(effect))
            if cls.diverges(effect):
                diverged_effect_ids.add(effect.pk)
                conflicts.append(
                    {
                        "kind": "diverged",
                        "member_id": effect.member_id,
                        "member_name": str(effect.member),
                        "round_id": locked_round.id,
                        "round_name": locked_round.name,
                        "detail": (
                            "Der aktuelle Stand weicht vom aufgezeichneten "
                            "Zustand der Runde ab."
                        ),
                    }
                )
        return conflicts, diverged_effect_ids

    @classmethod
    def _clear_contracts_created_at(cls, locked_round) -> None:
        if not locked_round.member_effects.filter(
            state=BiddingRoundMemberEffect.State.APPLIED
        ).exists():
            locked_round.contracts_created_at = None
            locked_round.save(update_fields=["contracts_created_at", "updated_at"])

    @classmethod
    def diverges(cls, effect) -> bool:
        subscriptions, contributions = cls.current_state(effect)
        return (
            subscriptions != effect.applied_subscriptions
            or contributions != effect.applied_contributions
        )

    @classmethod
    def _cross_round_conflicts(cls, effect) -> list[dict]:
        previous = cls._by_pk(effect.previous_subscriptions)
        applied = cls._by_pk(effect.applied_subscriptions)
        created = set(applied) - set(previous)
        touched = set(previous) | set(applied)

        if not touched:
            return []

        conflicts = cls._conflicts_from_other_effects(
            effect, created, touched, previous
        )
        conflicts.extend(cls._conflicts_from_foreign_links(effect, created))
        return cls._deduplicate_conflicts(conflicts)

    @classmethod
    def _conflicts_from_other_effects(
        cls, effect, created, touched, previous
    ) -> list[dict]:
        conflicts = []
        other_round_ids = BiddingRoundCreatedSubscription.objects.filter(
            subscription_id__in=touched
        ).values_list("round_id", flat=True)
        other_effects = (
            BiddingRoundMemberEffect.objects.filter(
                state=BiddingRoundMemberEffect.State.APPLIED,
                round_id__in=other_round_ids,
            )
            .exclude(round_id=effect.round_id)
            .select_related("round", "member")
        )
        for other in other_effects:
            detail = cls._detail_for_other_effect(
                created,
                touched,
                previous,
                cls._by_pk(other.previous_subscriptions),
                cls._by_pk(other.applied_subscriptions),
            )
            if detail is not None:
                conflicts.append(
                    cls._conflict(effect, other.round, other.member, detail)
                )
        return conflicts

    @staticmethod
    def _detail_for_other_effect(
        created, touched, previous, other_previous, other_applied
    ):
        if created & (set(other_previous) | set(other_applied)):
            return (
                "Die andere Runde nutzt einen Vertrag, den diese Rücknahme "
                "löschen würde."
            )
        for pk in touched - created:
            if pk in other_applied and other_applied[pk] != previous.get(pk):
                return (
                    "Die andere Runde hat diesen Vertrag nach dieser Runde "
                    "weiterverändert."
                )
        return None

    @classmethod
    def _conflicts_from_foreign_links(cls, effect, created) -> list[dict]:
        conflicts = []
        foreign_links = (
            BiddingRoundCreatedSubscription.objects.filter(subscription_id__in=created)
            .exclude(round_id=effect.round_id)
            .select_related("round", "subscription__member")
        )
        for link in foreign_links:
            conflicts.append(
                cls._conflict(
                    effect,
                    link.round,
                    link.subscription.member,
                    "Eine andere Runde hat diesen Vertrag erzeugt oder übernommen.",
                )
            )
        return conflicts

    @staticmethod
    def _deduplicate_conflicts(conflicts) -> list[dict]:
        unique = []
        seen = set()
        for conflict in conflicts:
            key = (conflict["round_id"], conflict["other_member_id"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(conflict)
        return unique

    @staticmethod
    def _conflict(effect, other_round, other_member, detail) -> dict:
        return {
            "kind": "cross_round",
            "member_id": effect.member_id,
            "member_name": str(effect.member),
            "round_id": other_round.id,
            "round_name": other_round.name,
            "other_member_id": other_member.id,
            "other_member_name": str(other_member),
            "detail": detail,
        }

    @classmethod
    def _revert_effect(cls, effect, actor, reason, force, diverged, cache) -> dict:
        applied_subscriptions = cls._by_pk(effect.applied_subscriptions)
        previous_subscriptions = cls._by_pk(effect.previous_subscriptions)
        created_subscription_ids = set(applied_subscriptions) - set(
            previous_subscriptions
        )
        deleted_subscriptions = 0
        if created_subscription_ids:
            deleted_subscriptions = Subscription.objects.filter(
                pk__in=created_subscription_ids
            ).count()
            Subscription.objects.filter(pk__in=created_subscription_ids).delete()
        for entry in effect.previous_subscriptions:
            cls._restore(entry)

        applied_contributions = cls._by_pk(effect.applied_contributions)
        previous_contributions = cls._by_pk(effect.previous_contributions)
        created_contribution_ids = set(applied_contributions) - set(
            previous_contributions
        )
        SolidarityContribution.objects.filter(pk__in=created_contribution_ids).delete()
        for entry in effect.previous_contributions:
            cls._restore(entry)
        cls._relink_contribution_logs(effect)

        cls._delete_orphan_mandate_refs(effect)
        BiddingRoundCreatedSubscription.objects.filter(
            round_id=effect.round_id, subscription__member_id=effect.member_id
        ).delete()

        BiddingRoundMemberRollbackLogEntry().populate(
            actor=actor,
            user=effect.member,
            round_name=effect.round.name,
            subscriptions_deleted=deleted_subscriptions,
            subscriptions_restored=len(effect.previous_subscriptions),
            contributions_restored=len(effect.previous_contributions),
            reason=reason,
            forced=force and diverged,
        ).save()

        effect.state = BiddingRoundMemberEffect.State.REVERSED
        effect.reversed_at = get_now(cache=cache)
        effect.reversed_by = actor
        effect.reversal_reason = reason
        effect.divergence_overridden = force and diverged
        effect.save()

        return cls._result(
            effect,
            state="reverted",
            subscriptions_deleted=deleted_subscriptions,
            subscriptions_restored=len(effect.previous_subscriptions),
            contributions_restored=len(effect.previous_contributions),
        )

    @classmethod
    def _relink_contribution_logs(cls, effect) -> None:
        existing_ids = set(
            SolidarityContribution.objects.filter(
                member_id=effect.member_id
            ).values_list("pk", flat=True)
        )
        for link in effect.contribution_log_links:
            updates = {}
            for field in ("old_contribution_id", "new_contribution_id"):
                value = link[field]
                if value in existing_ids:
                    updates[field] = value
            if updates:
                SolidarityContributionChangedLogEntry.objects.filter(
                    pk=link["pk"]
                ).update(**updates)

    @classmethod
    def _delete_orphan_mandate_refs(cls, effect) -> None:
        created = set(effect.created_mandate_ref_ids) - set(
            effect.previous_mandate_ref_ids
        )
        if not created:
            return
        used = set(
            Subscription.objects.filter(mandate_ref_id__in=created).values_list(
                "mandate_ref_id", flat=True
            )
        )
        MandateReference.objects.filter(pk__in=created - used).delete()

    @staticmethod
    def _restore(entry) -> None:
        for deserialized in serializers.deserialize("json", json.dumps([entry])):
            deserialized.save()

    @staticmethod
    def _by_pk(entries) -> dict:
        return {entry["pk"]: entry for entry in entries}

    @staticmethod
    def _result(
        effect,
        state,
        subscriptions_deleted=0,
        subscriptions_restored=0,
        contributions_restored=0,
        detail="",
    ) -> dict:
        return {
            "member_id": effect.member_id,
            "member_name": str(effect.member),
            "state": state,
            "subscriptions_deleted": subscriptions_deleted,
            "subscriptions_restored": subscriptions_restored,
            "contributions_restored": contributions_restored,
            "detail": detail,
        }
