"""
Service functions around the member number (Mitgliedsnummer).

Background (US 4.3 / Issue #535):
Previously, the member number was a plain integer sequence assigned at 03:00
on the first of each month by a Celery task. The format was hard-coded.

This module adds:

1. An admin-configurable **format** (prefix, length, zero-padding, start
   value) — see ``format_member_no``.
2. Immediate assignment at member creation time (no longer nightly) — see
   ``assign_member_no_if_eligible``.
3. The original Celery task is kept as a safety net that picks up members
   without a number — see ``tapir.wirgarten.tasks.generate_member_numbers``.
4. An optional toggle controlling whether members still in their trial
   period (coop trial or subscription trial) receive a number.

Important: ``Member.member_no`` stays an ``IntegerField`` in the database —
only the raw number is persisted. Prefix and zero-padding are applied at
display time only. This keeps sorting, import/export and lookup logic
unchanged.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Max

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


def format_member_no(member_no: int | None) -> str | None:
    """
    Format a raw member number (integer) according to the current admin
    configuration (prefix, length, zero-padding).

    Returns ``None`` when ``member_no`` itself is ``None``, so templates like
    ``{{ member.formatted_member_no|default:'-' }}`` keep working unchanged.

    Examples (prefix='BT', length=4, pad=True):
        17   -> 'BT0017'
        1234 -> 'BT1234'
        None -> None
    """
    if member_no is None:
        return None

    prefix = get_parameter_value(ParameterKeys.MEMBER_NUMBER_PREFIX) or ""
    length = get_parameter_value(ParameterKeys.MEMBER_NUMBER_LENGTH)
    zero_pad = get_parameter_value(ParameterKeys.MEMBER_NUMBER_ZERO_PAD)

    # Defensive default in case the parameter has not been imported yet
    # (e.g. in a young test DB without a `parameter_definitions` run).
    if not isinstance(length, int) or length < 1:
        length = 1

    number_str = f"{member_no:0{length}d}" if zero_pad else str(member_no)
    return f"{prefix}{number_str}"


def compute_next_member_no() -> int:
    """
    Return the next member number that should be assigned.

    The configured start value acts as a *lower bound*:
    - If no members have a number yet, start counting at ``start_value``.
    - If higher numbers already exist, return MAX+1.
    This lets an admin start the counter at e.g. 1000 without overwriting
    existing higher numbers.

    Race-condition note: ``MAX(member_no) + 1`` is not atomic. Parallel
    registrations can cause one transaction to fail with ``IntegrityError``
    (unique constraint on ``member_no``). This was intentionally left out
    of scope; if it actually bites, the fix is ``select_for_update()`` or
    a retry loop.
    """
    # Local import to avoid circular imports (service -> models -> service).
    from tapir.wirgarten.models import Member

    start_value = get_parameter_value(ParameterKeys.MEMBER_NUMBER_START_VALUE) or 1
    max_existing = Member.objects.aggregate(Max("member_no"))["member_no__max"] or 0
    return max(start_value, max_existing + 1)


def is_member_in_any_trial(member, cache: dict | None = None) -> bool:
    """
    True if the member is currently inside *any* trial period — either the
    coop trial (entry date in the future) or at least one subscription
    trial period.
    """
    # Local imports to avoid circular imports.
    from tapir.coop.services.membership_cancellation_manager import (
        MembershipCancellationManager,
    )
    from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager

    if cache is None:
        cache = {}

    if MembershipCancellationManager.is_in_coop_trial(member):
        return True

    # ``get_subscriptions_in_trial_period`` already respects the global
    # ``TRIAL_PERIOD_ENABLED`` parameter and returns an empty list if the
    # whole trial feature is off.
    trial_subs = TrialPeriodManager.get_subscriptions_in_trial_period(
        member_id=member.id, cache=cache
    )
    return len(trial_subs) > 0


def should_assign_member_no(member, cache: dict | None = None) -> bool:
    """
    Decide whether ``member`` should receive a member number right now.

    Rules:
    - If the member already has a number -> False (never overwrite).
    - If the admin disabled ``MEMBER_NUMBER_ASSIGN_DURING_TRIAL`` and the
      member is in any trial period -> False.
    - Otherwise -> True.

    The ``cache`` parameter is optional and is only forwarded to
    ``is_member_in_any_trial`` (repository convention for request-scoped
    caches).
    """
    if member.member_no is not None:
        return False

    assign_during_trial = get_parameter_value(
        ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL
    )
    if not assign_during_trial and is_member_in_any_trial(member, cache=cache):
        return False

    return True


@transaction.atomic
def assign_member_no_if_eligible(member, cache: dict | None = None) -> bool:
    """
    Assign a member number to ``member`` *immediately* if the rules in
    ``should_assign_member_no`` allow it.

    Returns ``True`` if a new number was assigned, ``False`` otherwise.

    Called from:
    - ``BestellWizardOrderFulfiller.create_member_and_fulfill_order`` for the
      direct wizard registration flow, *after* subscriptions and coop shares
      have been created (so the trial check sees the real state);
    - the admin modal ``get_member_personal_data_create_form`` (manual
      creation by an admin);
    - the safety-net task ``generate_member_numbers`` (scheduled catchall
      for members that somehow still have no number);
    - the management command ``backfill_member_numbers`` (one-off nudge for
      pre-existing members without a number).

    This service call intentionally does *not* fire the
    ``MEMBERSHIP_ENTRY`` mail trigger. That trigger is kept in the
    safety-net task so its original semantics ("member got their first
    number") are preserved and it never fires during a wizard transaction
    that has not yet committed.
    """
    if not should_assign_member_no(member, cache=cache):
        return False

    member.member_no = compute_next_member_no()
    member.save()
    return True
