# Plan: extra email addresses — own subscriptions, direct mails, former members leaving lists

Repo copy: `plans/member_extra_email_subscriptions_plan.md` (not under `docs/`, which mkdocs publishes).

## Goal

Every confirmed extra address has its own mail category registrations and mailman list subscriptions. It manages them through a temporary personalized link, sent from the member profile, requested through a new public form, or included in mails.

`receives_direct_mails` changes only two things:

| | `receives_direct_mails=True` | `receives_direct_mails=False` |
|---|---|---|
| Direct mails | Copy of every mail the main address gets, **except** when the member was reached through a mail category (transactional, time-triggered, mass mails to segments) | None |
| Starting registrations | Snapshot of the member's category registrations and list subscriptions at confirmation | Category defaults by category mode; no lists |

Category mails reach an extra address only through its own registrations, regardless of `receives_direct_mails`.

## What exists

### This repo

- `MemberExtraEmail` (`tapir/wirgarten/models.py:1140`): `member`, `email`, `first_name`, `last_name`, `confirmed_on`, `secret` (permanent UUID, used for confirmation). Unique on `(member, email)`; the same address can belong to several members.
- Log entries: created / updated / deleted / confirmed.
- `Member.get_extra_recipients(cache)` (`models.py:471`): confirmed extras if `ENABLE_EXTRA_MAIL_ADDRESSES` is on.
- `tapir/core/views/member_extra_emails.py`: CRUD API (`check_permission_or_self`), confirmation redirect + confirmed page. Confirmation mail via `Events.EXTRA_MAIL_CONFIRMATION`.
- Frontend: `src_frontend/member_profile/personal_data/MemberExtraEmailsModal.tsx`.
- Parameters: `ENABLE_EXTRA_MAIL_ADDRESSES`, `EXPLANATION_TEXT_EXTRA_MAIL_ADDRESSES` (`parameter_definitions_emails.py`). They are saved by the legacy Django form `ParameterView` (`tapir/configuration/views.py:39`), which has no change hooks.
- Mail categories, member side: `MemberMailCategoryDataApiView` (`tapir/core/views/general.py`). Shows categories whose dynamic segment contains the member; stores `InternalRecipientCategoryRegistration(internal_recipient_id=member.id)`. `InternalRecipientManager` applies the mode defaults. Card: `MemberMailCategoryCard.tsx`.
- Mailman (`tapir/core/views/mailing_lists.py`, `tapir/core/services/mailman/`):
  - No DB mirror. Subscriptions are address based and read live through `mailmanclient`. Every subscription goes through Tapir.
  - Gated by `settings.MAILING_LISTS_ENABLED`.
  - Member self-service: subscribe / unsubscribe / confirm / reject, main address only, advertised lists or lists the member is already on. Card: `MemberMailingListsCard.tsx`.
  - Admin: subscribe internal (member, by invitation), subscribe external address (invitation), unsubscribe by address, recipient list linking to the member profile by main address only.
- `MailChangeService.apply_mail_change` (`tapir/accounts/services/mail_change_service.py`) moves `StaticSegmentRecipient` rows to the new address, but not mailman subscriptions.

### Mail module (`tapir-mail-module`)

- Recipient resolution (`service/segment.py`):
  - Union of the dynamic segments (deduplicated), then category recipients (`add_mail_categories`), then static segments appended.
  - No deduplication across these sources: a member in a segment and in a category of the same mail gets it twice.
- Dispatch (`service/email_dispatch.py:153`): for each recipient, `get_extra_recipients(cache)` is called if it exists. One extra `EmailDispatch` is built per extra. Tokens resolve against the member; `first_name` / `last_name` are overridden.
- `MailCategoryRecipientResolver` (`service/mail_category_recipients_resolver.py`): dynamic segment filtered by mode and `InternalRecipientCategoryRegistration`, plus the static segment recipients. No host hook for extra recipients.
- External recipients: `ExternalRecipient` (permanent `secret_key`), `ExternalRecipientConfirmation`, and `StaticSegmentRecipient` in the category's static segment. There is a public registration form per category (`available_for_external_recipients=True` only) and a permanent management page.

### Why extras are not `ExternalRecipient`s

- External recipients only see categories with `available_for_external_recipients`. Extras need the member-only categories, the ones with a dynamic segment.
- Static segment recipients don't follow the member: they would keep receiving mails after the member leaves the segment, and they ignore the mode defaults.
- Static recipients don't resolve member tokens.

## Design

### Model

- `MemberExtraEmail.receives_direct_mails: BooleanField`. UI label "Erhält auch persönliche Mails (Verträge, Abholung, Rundmails an alle Mitglieder)"; badge "Persönliche Mails" / "Nur Abos". The migration sets `True` for existing rows; the field default for new rows is `True` as well.
- Category registrations of all extras reuse `InternalRecipientCategoryRegistration` with `internal_recipient_id=extra_email.id`. Both ids are nanoids of length 10, so a collision is negligible.
- Category defaults for extras: same as `InternalRecipientManager`, except that `ALWAYS_ON` counts as `OPTIONAL_DEFAULT_ON`. The extra address is voluntary, and the mandatory mails still reach the main address.
- Changing `receives_direct_mails` after confirmation only switches the direct mails. Registrations and subscriptions stay as they are.

### Snapshot at confirmation (`receives_direct_mails=True`)

New service `MemberExtraEmailRegistrationSnapshotter.snapshot(extra_email, cache)`, called from `ConfirmMemberExtraEmailApiView` when `receives_direct_mails` is set:
- For each category whose dynamic segment contains the member: one explicit `InternalRecipientCategoryRegistration(internal_recipient_id=extra.id, is_registered=<member's effective state>)`. Explicit rows keep the snapshot stable if the category mode changes later.
- For each list the main address is subscribed to (confirmed, not pending invitations): subscribe the extra with `pre_verified`, `pre_confirmed`, `pre_approved` and `send_welcome_message=False`.

Mailman calls run in `transaction.on_commit`, so a rollback doesn't leave mailman subscribed and a mailman error doesn't roll back the confirmation.

Extras without direct mails get nothing at confirmation: the category defaults apply, and they have no lists.

### Mail module changes

1. **`AddressedRecipient`** dataclass in the mail module:
   - `recipient`: the base object that tokens are resolved against.
   - `email`.
   - `token_overrides: dict`.
   - It never gets extras.

   Dispatch builds exactly one `EmailDispatch` for it. Tokens resolve against `recipient`, then `token_overrides` are applied. This replaces the current hard-coded `first_name` / `last_name` override.
2. **`get_extra_recipients(cache)`** returns `list[AddressedRecipient]`. Wirgarten returns confirmed extras with `receives_direct_mails`, with overrides for `first_name`, `last_name` and the manage link token.
3. **Category recipients don't get copies:** `add_mail_categories` wraps internal category recipients as `AddressedRecipient(member, member.email, {})`.
4. **Category hook:** `register_additional_category_recipients_provider(fn)` in `registries.py`, with `fn(mail_category, cache) -> list[AddressedRecipient]`. `MailCategoryRecipientResolver.resolve_recipients` appends its result and takes a `cache` parameter; the callers are adapted (`serializers.py:424`, `segment.py:163`).
5. **Deduplication by email per config dispatch**, first occurrence wins. Dynamic segment recipients come first, so a member reached through both a segment and a category gets the segment version, with copies. This also fixes the existing double send for members in a segment and a category of the same mail.
6. Release a new tapir-mail version and bump the wheel URL in `pyproject.toml`.

Wirgarten category provider:
- Takes all confirmed extras whose member is in the category's unfiltered dynamic segment. The member's own registration doesn't matter.
- Filters them by their own registrations and the extra defaults.
- Returns `AddressedRecipient(member, extra.email, overrides)`.
- Returns `[]` if `ENABLE_EXTRA_MAIL_ADDRESSES` is off.

### Mailman for extras

New service `tapir/core/services/mailman/extra_email_mailing_list_manager.py`:
- `subscribe(extra_email, mailing_list)` / `unsubscribe(...)`: self-service rules, the same as for members.
- `unsubscribe_from_all(email, cache)`: called on extra deletion (by the member, an admin or self-removal). It skips the call if the same address is still a confirmed extra elsewhere or a main address.

Admin recipient list (`MailingListRecipientListView`):
- Links extra addresses to their member's profile.
- Marks extra addresses as such.

### Disabling the feature

When `ENABLE_EXTRA_MAIL_ADDRESSES` is switched off, nothing is deleted or unsubscribed:
- Extra addresses, category registrations and mailman subscriptions stay as they are. Extras keep receiving list mails.
- Tapir stops sending to extras: the category provider and `get_extra_recipients` return nothing.
- The member profile modal, the access link pages and the request page are disabled, like the existing extra email views (`FEATURE_DISABLED_MESSAGE`).
- Admins can still remove extra addresses from lists through the recipient list.
- Switching the feature back on restores everything as it was.

Update the description of `ENABLE_EXTRA_MAIL_ADDRESSES` in `parameter_definitions_emails.py`:
- Describe both variants (with and without direct mails).
- State that switching it off only stops Tapir's mails to extra addresses and the management pages. Existing addresses, registrations and mailing list subscriptions are kept, and extras stay on their lists until an admin removes them.

### Access link

- Token: `django.core.signing.TimestampSigner` with a dedicated salt, payload `extra_email.id`, `max_age` from a new parameter `EXTRA_MAIL_ACCESS_LINK_VALIDITY_HOURS` (default 72). No table is needed. Deleting the extra invalidates its tokens.
- Link target: `/extra_email/manage/<token>`, a public Django template page with a new React island (`add-frontend-entry` skill).
- Sending the link:
  - Member profile: a "Link senden" button per confirmed extra in `MemberExtraEmailsModal`. `POST api/member_extra_email_send_access_link` with `check_permission_or_self`.
  - Public page `/extra_email/request_access`: email field → mail with one link per matching confirmed extra. If an address is an extra of several members, the mail lists them by member first name. The response is always the same, so the page doesn't reveal which addresses exist.
  - The confirmed page offers an "Abos verwalten" button that leads directly to a fresh link.
- New transactional trigger `Events.EXTRA_MAIL_ACCESS_LINK` with the tokens `access_link`, `main_mail_address` and `validity`.
- New recipient token "Abos verwalten Link":
  - For extras (through `token_overrides`): a fresh signed link.
  - For the main address: the member profile URL.
  - Admins can put it in layout footers.
  - An expired link in an older mail leads to the "Link abgelaufen" state, with a button to the request page.

### Management API

All endpoints are public (`permission_classes = []`). The token is validated in the view; an invalid or expired token returns 403.

- `GET api/extra_email_access/data?token=`:
  - `receives_direct_mails`, main address.
  - Categories, using the same selection as for the member, with the extra's registration states and the extra defaults.
  - Mailing lists, if enabled: advertised lists plus lists the address is already on, with their subscribed state.
- `POST api/extra_email_access/categories`: same semantics as `MemberMailCategoryDataApiView.post`, with `internal_recipient_id=extra.id`.
- `POST api/extra_email_access/mailing_list_subscribe` and `.../mailing_list_unsubscribe`: `{token, list_name}`.
- `DELETE api/extra_email_access?token=`: self-removal. It logs `MemberExtraEmailDeletedLogEntry` with `actor=None`, runs `unsubscribe_from_all` and deletes the extra. The member is not notified.
- Extract the shared logic from `MemberMailCategoryDataApiView` and the member self-service views into services that take a recipient id or an address, so the member and extra paths share it.
- Throttling (optional, decided at the beginning of phase 6): DRF `ScopedRateThrottle` on the request-link endpoint and the token endpoints. Nothing in the repo uses throttling yet; it needs `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.

### Member email change

`MailChangeService.apply_mail_change`: for each list the old address is subscribed to, subscribe the new address with the pre-flags and no welcome message, then unsubscribe the old one. Runs in `on_commit`. Pending invitations for the old address are discarded.

### Members leaving the organisation

When a member leaves the organisation, their main address and all their extra addresses are removed from every list. This also applies to members without extras, so it closes an existing gap.

**Who counts as former member** (new service `FormerMemberProvider.get_former_member_ids(reference_date, cache)`), depending on `ORGANISATION_LEGAL_STATUS`:
- Cooperative: no shares at the reference date and no future `PURCHASE` / `TRANSFER_IN` (same queries as in `MemberSegmentProvider.get_queryset_active_members`).
- Association: no `AssociationMembership` active at or after the reference date.
- Company: no active or future subscriptions (`get_active_and_future_subscriptions`).

**Nightly celery beat task** `unsubscribe_former_members_from_mailing_lists`:
- Gated by `MAILING_LISTS_ENABLED`. Runs regardless of `ENABLE_EXTRA_MAIL_ADDRESSES`, so extras of former members are removed even while the feature is off.
- Reads each list's subscribers and pending requests once, intersects them with the addresses of former members (main + all extras), then unsubscribes them (`pre_confirmed`, `pre_approved`) and discards their pending requests.
- Idempotent, so it needs no marker field. It catches up after downtime, and its first run cleans up members who left before the deploy.
- Logs `MemberUnsubscribedFromMailingListsLogEntry` (addresses + lists) on the member, only when something was removed.

**Blocking new subscriptions**, otherwise the next run would undo them:
- Member self-service (subscribe, confirm invitation) and the extras' access link endpoints refuse former members and their extras. The member profile card and the access page hide the subscribe buttons and show a hint instead.
- The admin views (subscribe internal, subscribe external) refuse addresses that belong to a former member, with an explanation.
- The snapshot at confirmation skips the lists if the member has already left.

Rejoining restores nothing: the member subscribes again through self-service.

**Deleting a member** ("Mitglied löschen", `DeleteMemberApiView`, `tapir/coop/views.py:351`): the nightly task can't catch this, because the `Member` row and the link to the extras are gone. The view therefore:
- Collects the main address and all extra addresses before deleting.
- Runs `unsubscribe_from_all` for each in `transaction.on_commit`. It also discards pending invitations and skips addresses still used by another member.
- Deletes the `InternalRecipientCategoryRegistration` rows of the member's id and the extras' ids (plain string ids, no cascade).

### UI changes

- `MemberExtraEmailsModal`:
  - `receives_direct_mails` checkbox on create and in edit.
  - Badge "Persönliche Mails" / "Nur Abos" per address.
  - "Link senden" button.
  - Update the explanation text parameter's default to describe both variants.
- New island `extra_email_access`:
  - Categories card + mailing lists card, visually reusing `MemberMailCategoryCard` and `MemberMailingListsCard` where possible.
  - "Adresse entfernen" button, with the confirmation in the same modal.
- Public request page: a simple form.

### Logging

- `MemberExtraEmailSubscriptionsChangedLogEntry` (address + diff) on the member, for category and list changes made through the access link.
- Changes of `receives_direct_mails` are covered by `MemberExtraEmailUpdatedLogEntry`.

## Phases

- [ ] Phase 0 — consider merging the mail module into this repo first. If merged, phase 1 is done in this repo: the category provider hook and the release + wheel bump are dropped, and the resolver queries `MemberExtraEmail` directly.
- [ ] Phase 1 — mail module: `AddressedRecipient`, category recipients without copies, category provider hook, dedup by email; tests, release, bump wheel
- [ ] Phase 2 — `receives_direct_mails` field + migration, `get_extra_recipients` returns `AddressedRecipient`s, API/serializer/modal checkbox
- [ ] Phase 3 — category provider + extra defaults, snapshot at confirmation (categories + lists)
- [ ] Phase 4 — extra mailing list manager, unsubscribe on deletion, recipient list display, parameter description update
- [ ] Phase 5 — access token service, send-link endpoint + trigger, public request page, "Abos verwalten Link" token
- [ ] Phase 6 — management API + island (categories, lists, self-removal), log entry, throttling (optional: decide at the beginning of the phase whether it's necessary; if yes, it also covers the phase 5 request-link endpoint)
- [ ] Phase 7 — mailman subscriptions follow the member's email change
- [ ] Phase 8 — former members: `FormerMemberProvider`, nightly unsubscription task + log entry, blocking new subscriptions (self-service, access link, admin views, snapshot), list unsubscription + registration cleanup in `DeleteMemberApiView`
- [ ] Phase 9 — test data generation (extras with and without direct mails, with registrations)
- [ ] Phase 10 — docs (`docs/admins`, explanation text)
- [ ] Phase 11 — delete this plan file (`plans/member_extra_email_subscriptions_plan.md`)

## Migration note

Existing confirmed extras get `receives_direct_mails=True` but no registrations. Without a backfill, they would lose category mails they get today as copies, or fall back to the category defaults. A one-off management command `snapshot_existing_extra_emails` runs the full snapshot (categories + lists) for every existing confirmed extra after deploy. It is not a data migration, because it needs the segment registry and mailman.
