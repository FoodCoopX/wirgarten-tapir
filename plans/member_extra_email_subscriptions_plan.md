# Plan: extra email addresses — own subscriptions, direct mails, former members leaving lists

Repo copy: `plans/member_extra_email_subscriptions_plan.md` (not under `docs/`, which mkdocs publishes).

## Goal

Every confirmed extra address has its own mail category registrations and mailman list subscriptions.

Every address that receives mails from Tapir can manage all its subscriptions through a single mail token:
- A member's main address leads to the member profile.
- Any other address (extra, external recipient, or both) leads to one public page for that address, reached through a temporary signed link. The link is also sent from the member profile, requested through a public form, and offered after confirming an extra.

An address has at most one owner: it is either the main address of one member or the confirmed extra of one member. Being an external recipient as well is allowed.

`receives_direct_mails` changes only two things:

| | `receives_direct_mails=True` | `receives_direct_mails=False` |
|---|---|---|
| Direct mails | Copy of every mail the main address gets (transactional, time-triggered, mass mails to segments), **except** when the member was reached through a mail category | None |
| Starting registrations | Snapshot of the member's category registrations and list subscriptions at confirmation | Category defaults by category mode; no lists |

Category mails reach an extra address only through its own registrations, regardless of `receives_direct_mails`.

## What exists

### This repo

- `MemberExtraEmail` (`tapir/wirgarten/models.py:1140`): `member`, `email`, `first_name`, `last_name`, `confirmed_on`, `secret` (permanent UUID, used for confirmation). Unique on `(member, email)`; the same address can be confirmed for several members, and can also be a member's main address.
- Log entries: created / updated / deleted / confirmed.
- `Member.get_extra_recipients(cache)` (`models.py:472`): confirmed extras if `ENABLE_EXTRA_MAIL_ADDRESSES` is on.
- `tapir/core/views/member_extra_emails.py`: CRUD API (`check_permission_or_self`), confirmation redirect + confirmed page. Confirmation mail via `Events.EXTRA_MAIL_CONFIRMATION`.
- Frontend: `src_frontend/member_profile/personal_data/MemberExtraEmailsModal.tsx`.
- Parameters: `ENABLE_EXTRA_MAIL_ADDRESSES`, `EXPLANATION_TEXT_EXTRA_MAIL_ADDRESSES` (`parameter_definitions_emails.py`). They are saved by the legacy Django form `ParameterView` (`tapir/configuration/views.py:39`), which has no change hooks.
- Mail categories, member side: `MemberMailCategoryDataApiView` (`tapir/core/views/general.py`). Shows categories whose dynamic segment contains the member; stores `InternalRecipientCategoryRegistration(member=member)`; `post` deletes all the member's registrations and recreates the submitted ones. `InternalRecipientManager` applies the mode defaults. Card: `MemberMailCategoryCard.tsx`.
- Mailman (`tapir/core/views/mailing_lists.py`, `tapir/core/services/mailman/`):
  - No DB mirror. Subscriptions are address based and read live through `mailmanclient`. Every subscription goes through Tapir.
  - Gated by `settings.MAILING_LISTS_ENABLED`.
  - Member self-service: subscribe / unsubscribe / confirm / reject, main address only, advertised lists or lists the member is already on. Card: `MemberMailingListsCard.tsx`.
  - Admin: subscribe internal (member, by invitation), subscribe external address (invitation), unsubscribe by address, recipient list linking to the member profile by main address only.
- `MailChangeService.apply_mail_change` (`tapir/accounts/services/mail_change_service.py`) moves `StaticSegmentRecipient` rows to the new address, but not mailman subscriptions.

### Mail module (`tapir/mail`)

- Recipient resolution (`resolve_segments` in `services/segment.py`):
  - Union of the dynamic segments (deduplicated), then category recipients (`add_mail_categories`), then static segments appended, then subtractive static segments removed by email, then transactional overrides applied (`apply_recipient_override`: keeps the recipient whose `id` matches `recipient_id_in_base_queryset`, or returns a single `TransactionalTriggerData.RecipientOutsideOfBaseQueryset`).
  - No deduplication across these sources: a member in a segment and in a category of the same mail gets it twice.
  - Callers: `_create_email_dispatches` (through `RecipientListProvider`), `OnboardingTrigger._on_create` (`tapir/wirgarten/triggers/onboarding_trigger.py:44`, one config dispatch per recipient, reads `recipient.subscription_set`), and the admin preview `SegmentViewSet.combine` (`tapir/mail/views/segments.py:97`, count + list).
  - `RecipientListProvider.get_recipient_list_from_email_configuration_dispatch` has a branch for sent dispatches returning `EmailDispatch.recipient` (an email string). Its only caller filters on `is_sent=False`, so the branch is dead.
- Dispatch (`services/email_dispatch.py:153`): for each recipient, `get_extra_recipients(cache)` is looked up by name (`getattr`, a leftover from the separate package) and called if it exists. One extra `EmailDispatch` is built per extra. Tokens resolve against the member; `first_name` / `last_name` are overridden.
- Every registered dynamic segment returns a `Member` queryset.
- `MailCategoryRecipientResolver` (`services/mail_category_recipients_resolver.py`): dynamic segment filtered by mode and `InternalRecipientCategoryRegistration`, plus the static segment recipients.
- External recipients: `ExternalRecipient` (permanent `secret_key`, `first_name`), `ExternalRecipientConfirmation`, and `StaticSegmentRecipient` in the category's static segment. There is a public registration form per category (`available_for_external_recipients=True` only) and a permanent management page (`external/manage/<secret>`, `ExternalRecipientManagementView`, Django form): edits `first_name` and the category registrations, and deletes the `ExternalRecipient` when no category is left.
- Mail tokens (`services/token.py`): "Empfänger" tokens (attribute names or callables), "Empfänger (extra)" dynamic tokens (callables taking the recipient object) and "Allgemein" tokens. `AddressedRecipient.token_overrides` are applied to "Empfänger" tokens only (`email_dispatch.py:148`).
- Dynamic token "Newsletter - Verwaltungslink" (`NewsletterManagementLinkProvider`, `tapir/core/services/`): member profile for members and for static recipients whose address is a main address, external management page for external recipients, `""` otherwise. The member profile URL is relative (no `SITE_URL`), so it doesn't work in mails. Extras get their member's profile link, which they can't use.

### Why extras are not `ExternalRecipient`s

- External recipients only see categories with `available_for_external_recipients`. Extras need the member-only categories, the ones with a dynamic segment.
- Static segment recipients don't follow the member: they would keep receiving mails after the member leaves the segment, and they ignore the mode defaults.
- Static recipients don't resolve member tokens.

## Design

### Model

- `MemberExtraEmail.receives_direct_mails: BooleanField`. UI label "Erhält auch persönliche Mails (Verträge, Abholung, Rundmails an alle Mitglieder)"; badge "Persönliche Mails" / "Nur Abos". Default `True`.
- `InternalRecipientCategoryRegistration` references its recipient through two nullable foreign keys, `member` and `member_extra_email` (cascade on delete). A check constraint requires exactly one of them; unique constraints allow one registration per category and recipient.
- Category defaults for extras: same as `InternalRecipientManager`, except that `ALWAYS_ON` counts as `OPTIONAL_DEFAULT_ON`. The extra address is voluntary, and the mandatory mails still reach the main address. The rule lives in `MemberExtraRecipientProvider`, as a queryset in `get_category_recipients` and per extra in the counterpart of `InternalRecipientManager.is_member_registered_to_mail_category`.
- Changing `receives_direct_mails` after confirmation only switches the direct mails. Registrations and subscriptions stay as they are: an extra created without direct mails and switched on later gets no snapshot, keeps the defaults and has no lists.

### Address ownership

An address is either the main address of one member or the confirmed extra of one member, never both. Unconfirmed extras with the same address may exist on several members; only one of them can be confirmed. An `ExternalRecipient` with the same address is allowed in both cases: external recipients only see the public categories, so the management page shows both parts without overlap.

- **Creating an extra** refuses only the member's own main address and the member's own existing extras. Refusing addresses of other members here would tell the member that someone else uses the address.
- **Confirming an extra** (`ConfirmMemberExtraEmailApiView`) is refused if the address is a member's main address or a confirmed extra of another member. Only the address owner sees this. The confirmation page shows "Diese Adresse ist bereits die Hauptadresse eines Mitglieds" or "Diese Adresse ist bereits als zusätzliche Adresse eines anderen Mitglieds bestätigt"; `confirmed_on` stays empty and nothing is logged.
- **An address becoming a main address wins**: on a confirmed email change (`MailChangeService.apply_mail_change`) and on member creation, every extra with that address is deleted, the member's own one included, with a `MemberExtraEmailDeletedLogEntry` (`actor=None`) on its member. The extra's member is not notified. Its category registrations cascade; its list subscriptions stay, since the address is still in use. One service holds this, called from `apply_mail_change` and from every member creation path (to be listed at the beginning of phase 5: Bestellwizard, admin creation, importers).
  - On an email change, the new address's owner has proved access through the confirmation link.
  - On member creation, they haven't: the Bestellwizard creates the member before the Keycloak verification, and Tapir has no hook on verification. A registration with someone else's address therefore removes that address's extra right away. This is accepted: such a registration already causes bigger problems (contracts, SEPA mandate, misdirected mails) that admins handle, and the extra can be added again once the member is deleted.

### Snapshot at confirmation (`receives_direct_mails=True`)

`MemberExtraEmailRegistrationSnapshotter.snapshot(extra_email, cache)`, called from `ConfirmMemberExtraEmailApiView` on the first confirmation only, when `receives_direct_mails` is set:
- For each category whose dynamic segment contains the member: one explicit `InternalRecipientCategoryRegistration(member_extra_email=extra, is_registered=<member's effective state>)`. Explicit rows keep the snapshot stable if the category mode changes later.
- For each list the main address is subscribed to (confirmed, not pending invitations): subscribe the extra with `pre_verified`, `pre_confirmed`, `pre_approved` and `send_welcome_message=False`.

Mailman calls run in `transaction.on_commit`, so a rollback doesn't leave mailman subscribed and a mailman error doesn't roll back the confirmation.

Extras without direct mails get nothing at confirmation: the category defaults apply, and they have no lists.

### Mail module

1. **`AddressedRecipient`** dataclass in `tapir/mail`:
   - `recipient`: the base object that tokens are resolved against.
   - `email`.
   - `token_overrides: dict`.

   Recipient resolution (`services/segment.py`) returns only `list[AddressedRecipient]`. Dispatch builds exactly one `EmailDispatch` per entry. Tokens resolve against `recipient`, then `token_overrides` are applied to the "Empfänger" and "Empfänger (extra)" tokens, keyed by their storage key.

   Order in `resolve_segments`:
   1. Dynamic segments, each member expanded into main address + direct-mail extras.
   2. Category recipients, then static segment recipients, without copies.
   3. Subtractive static segments, by email: an extra address in a subtractive static segment is removed too.
   4. Transactional overrides: `apply_recipient_override` keeps every entry whose `recipient.id` matches, so transactional mails keep their copies. `RecipientOutsideOfBaseQueryset` is wrapped without extras.
   5. Deduplication by email.

   Other callers:
   - `OnboardingTrigger._on_create` iterates the distinct `Member`s (`addressed.recipient`), not the addresses.
   - `SegmentViewSet.combine` counts and lists every address, extras included and marked as such, since they receive the mail. The category recipient count (`serializers.py:424`) counts the extras as well.
   - `RecipientListProvider` only resolves unsent dispatches.
2. **Direct-mail copies are expanded during resolution:** members from dynamic segments become their main address plus their direct-mail extras. `MemberExtraRecipientProvider.get_direct_mail_recipients(member, cache) -> list[AddressedRecipient]` (`tapir/core/services/`) returns confirmed extras with `receives_direct_mails`, with overrides for `first_name`, `last_name` and the management link token, and `[]` if `ENABLE_EXTRA_MAIL_ADDRESSES` is off.
3. **Category and static recipients don't get copies:** `MailCategoryRecipientResolver.resolve_recipients` returns `list[AddressedRecipient]`, with internal category recipients as `AddressedRecipient(member, member.email, {})` and its static segment recipients wrapped the same way. `add_static_segments` wraps static segment recipients the same way.
4. **Extras in categories:** `MailCategoryRecipientResolver.resolve_recipients` takes a `cache` parameter and appends the extras' `AddressedRecipient`s, queried directly from `MemberExtraEmail`.
5. **Deduplication by email per config dispatch**, a single pass over the resolved list, first occurrence wins. Dynamic segment recipients come first, so a member reached through both a segment and a category gets the mail once, in the segment version, with copies.

Extra recipients of a category:
- All confirmed extras whose member is in the category's unfiltered dynamic segment. The member's own registration doesn't matter.
- Filters them by their own registrations and the extra defaults.
- Returns `AddressedRecipient(member, extra.email, overrides)`.
- Returns `[]` if `ENABLE_EXTRA_MAIL_ADDRESSES` is off.

### Mailman

`MailingListUnsubscriber.unsubscribe_from_all(email, cache)` (`tapir/core/services/mailman/mailing_list_unsubscriber.py`):
- Unsubscribes the address from every list and discards its pending requests.
- Keeps addresses that are a main address or an `ExternalRecipient`.
- Called after commit whenever an address may have lost its last owner: deletion of a confirmed extra (by the member, an admin or on the management page), deletion of an `ExternalRecipient` on the management page, and member deletion.

Subscribe / unsubscribe on the management page use the address-based list self-service (see management API), with the same rules as for members.

Admin recipient list (`MailingListRecipientListView`):
- Links an extra address to its member's profile.
- Marks extra addresses as such, with the name and main address of their member.

### Disabling the feature

When `ENABLE_EXTRA_MAIL_ADDRESSES` is switched off, nothing is deleted or unsubscribed:
- Extra addresses, category registrations and mailman subscriptions stay as they are. Extras keep receiving list mails.
- Tapir stops sending to extras: the category resolver skips them and `MemberExtraRecipientProvider` returns nothing.
- The member profile modal is disabled (`FEATURE_DISABLED_MESSAGE`).
- The management page and the request page stay available for external recipients and mailing lists. The extra part of the page is hidden, and its endpoints refuse changes.
- Admins can still remove extra addresses from lists through the recipient list.
- Switching the feature back on restores everything as it was.

The description of `ENABLE_EXTRA_MAIL_ADDRESSES` (`parameter_definitions_emails.py`):
- Describes both variants (with and without direct mails).
- States that switching it off only stops Tapir's mails to extra addresses and their management. Existing addresses, registrations and mailing list subscriptions are kept, and extras stay on their lists until an admin removes them.

### Management link

**Token** "Empfänger (extra).Newsletter - Verwaltungslink". Its name is the one already used in templates and layout footers. It resolves by the address the mail is sent to, not by the recipient object:
- A member's main address: absolute member profile URL.
- Any other address: the management page link, freshly signed at dispatch time.

`SubscriptionManagementLinkProvider` (`tapir/core/services/`) builds the link from the address. The address reaches it as follows:
- Members, static segment recipients and `RecipientOutsideOfBaseQueryset` carry it as `.email`.
- Extras get the link through `token_overrides` (`MemberExtraRecipientProvider._build_addressed_recipient`).

**Signed link**: `django.core.signing.TimestampSigner` with a dedicated salt, payload the normalised address (`EmailNormaliser`), `max_age` from a new parameter `SUBSCRIPTION_MANAGEMENT_LINK_VALIDITY_HOURS` (default 72), not gated by `ENABLE_EXTRA_MAIL_ADDRESSES`. No table is needed. A link stays valid until it expires even if the address loses all its subscriptions; the page then has nothing to show.

**Page** `/subscriptions/manage/<token>`: a public Django template page with a new React island `subscription_management` (`add-frontend-entry` skill).
- Invalid or expired token: "Link abgelaufen", with a button to the request page.
- Address that is now a member's main address: redirect to the member profile.
- Otherwise: the address, then the parts described under management API.

**Sending the link**:
- Member profile: a "Link senden" button per confirmed extra in `MemberExtraEmailsModal`. `POST api/member_extra_email_send_management_link` with `check_permission_or_self`.
- Public page `/subscriptions/request_link`: email field. A main address gets a mail with the profile link; a confirmed extra or an `ExternalRecipient` gets a mail with the management link; any other address gets nothing. The response is always the same, so the page doesn't reveal which addresses exist.
- The extra's confirmed page offers an "Abos verwalten" button: its permanent `secret` proves ownership, so it redirects to a fresh signed link.
- The external recipients' permanent link `external/manage/<secret>`, contained in many old mails, redirects to a fresh signed link the same way.
- Transactional trigger `Events.SUBSCRIPTION_MANAGEMENT_LINK` with the tokens `management_link` and `validity`, sent to `RecipientOutsideOfBaseQueryset(email=address, first_name=…)`: the extra's or the external recipient's first name. Required, with a draft in `tapir/wirgarten/email_drafts/`.

### Management API

All endpoints are public (`permission_classes = []`). The token is validated in the view; an invalid or expired token returns 403.

- `GET api/subscription_management/data?token=`:
  - Extra part, if the address is a confirmed extra and `ENABLE_EXTRA_MAIL_ADDRESSES` is on: the member's first name, `receives_direct_mails`, categories using the same selection as for the member, with the extra's registration states and the extra defaults.
  - External part, if the address is an `ExternalRecipient`: `first_name`, the categories with `available_for_external_recipients` and their registration states.
  - Mailing lists, if enabled: advertised lists plus lists the address is already on, with their subscribed state.
- `POST api/subscription_management/extra_categories`: updates or creates a registration (`member_extra_email=extra`) for each submitted category only, and never deletes other rows: rows for categories outside the member's current segment must survive.
- `POST api/subscription_management/external`: `first_name` and category registrations through `ExternalRecipientManager`. Registering to a new public category needs no confirmation mail, since the token proves access to the address.
- `POST api/subscription_management/mailing_list_subscribe` and `.../mailing_list_unsubscribe`: `{token, list_name}`.
- `DELETE api/subscription_management/extra?token=`: leave the member. It logs `MemberExtraEmailDeletedLogEntry` with `actor=None`, deletes the extra and runs `unsubscribe_from_all` after commit. The member is not notified.
- `DELETE api/subscription_management/external?token=`: deletes the `ExternalRecipient` and its static segment rows, then runs `unsubscribe_from_all` after commit.
- Services shared by the member and the management page endpoints:
  - Category registrations: take a `Member` or a `MemberExtraEmail`, with the same update-or-create semantics for both (`MemberMailCategoryDataApiView.post` included).
  - Category selection (categories whose dynamic segment contains the member): used by `MemberMailCategoryDataApiView.get`, the management page and `MemberExtraEmailRegistrationSnapshotter`.
  - Mailing lists: subscribe / unsubscribe take an address, used by the member views and the management page endpoints.
- Throttling (optional, decided at the beginning of phase 7): DRF `ScopedRateThrottle` on the request-link endpoint and the token endpoints. Nothing in the repo uses throttling yet; it needs `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.

### Member email change

`MailChangeService.apply_mail_change`: for each list the old address is subscribed to, subscribe the new address with the pre-flags and no welcome message, then unsubscribe the old one. Runs in `on_commit`. Pending invitations for the old address are discarded.

### Members leaving the organisation

When a member leaves the organisation, their main address and all their extra addresses are removed from every list, whether or not they have extras.

**Who counts as former member**: every member who isn't active. Active is the definition of the "Aktive Mitglieder" segment, independent of `ORGANISATION_LEGAL_STATUS`: shares at the reference date, future `PURCHASE` / `TRANSFER_IN`, active or future subscriptions, association membership, or solidarity contribution. Mass mails and list membership thus agree on who is a member.

`ActiveMemberProvider` (`tapir/core/services/active_member_provider.py`) is the single definition of active members:
- `get_active_members(reference_datetime, cache)`, both parameters required.
- `get_former_members(reference_datetime, cache)`: all members excluding the active ones.
- Used by the `ALL_USERS` segment in `tapir/coop/apps.py` (through a lambda that passes the current datetime and a fresh cache, since mail segment getters take no arguments), `UnverifiedMembersService`, `send_verify_emails` and the nightly task.

**Nightly celery beat task** `unsubscribe_former_members_from_mailing_lists`:
- Gated by `MAILING_LISTS_ENABLED`. Runs regardless of `ENABLE_EXTRA_MAIL_ADDRESSES`, so extras of former members are removed even while the feature is off.
- Reads each list's subscribers and pending requests once, intersects them with the addresses of former members (main + all extras), then unsubscribes them (`pre_confirmed`, `pre_approved`) and discards their pending requests.
- Idempotent, so it needs no marker field. It catches up after downtime, and its first run cleans up members who left before the deploy.
- Logs `MemberUnsubscribedFromMailingListsLogEntry` (addresses + lists) on the member, only when something was removed.

**Blocking new subscriptions**, otherwise the next run would undo them:
- Member self-service (subscribe, confirm invitation) and the management page endpoints refuse former members and their extras. The member profile card and the management page hide the subscribe buttons and show a hint instead.
- The admin views (subscribe internal, subscribe external) refuse addresses that belong to a former member, with an explanation.
- The snapshot at confirmation skips the lists if the member has already left. The check runs in `snapshot` before registering the `on_commit` callback, since `_snapshot_mailing_lists` only receives addresses.

Rejoining restores nothing: the member subscribes again through self-service.

**Deleting a member** ("Mitglied löschen", `DeleteMemberApiView`, `tapir/coop/views.py:351`): the nightly task can't catch this, because the `Member` row and the link to the extras are gone. The view therefore:
- Collects the main address and all extra addresses before deleting.
- Runs `unsubscribe_from_all` for each in `transaction.on_commit`.

### UI changes

- `MemberExtraEmailsModal`:
  - `receives_direct_mails` checkbox on create and in edit.
  - Badge "Persönliche Mails" / "Nur Abos" per address.
  - "Link senden" button.
  - The explanation text parameter's default describes both variants.
- Island `subscription_management`:
  - Extra part: categories card and "Nicht mehr zusätzliche Adresse von {Vorname}" button.
  - External part: first name, public categories card and "Abmelden" button.
  - Mailing lists card.
  - Cards visually reuse `MemberMailCategoryCard` and `MemberMailingListsCard` where possible; removals confirm in the same modal.
- Public request page: a simple form.

### Logging

- `MemberExtraEmailSubscriptionsChangedLogEntry` (address + diff) on the member, for category and list changes of an extra made through the management page. Changes of external recipients are not logged: there is no member to log on.
- Changes of `receives_direct_mails` are covered by `MemberExtraEmailUpdatedLogEntry`.

## Phases

- [x] Phase 0 — merge the mail module into this repo (#1447)
- [x] Phase 1 — mail module (`tapir/mail`): `AddressedRecipient`, resolution returns only `AddressedRecipient`s (segment members expanded through `MemberExtraRecipientProvider`, replacing `Member.get_extra_recipients` and the `getattr` lookup; step order, override matching, onboarding trigger, preview, dead branch), category and static recipients without copies, dedup by email; tests
- [x] Phase 2 — `receives_direct_mails` field + migration, `MemberExtraRecipientProvider` filters on it, API/serializer/modal checkbox
- [x] Phase 3 — extras in `MailCategoryRecipientResolver` + extra defaults, snapshot at confirmation (categories + lists), data migration for existing extras
- [x] Phase 4 — extra mailing list manager (`unsubscribe_from_all`), unsubscribe on deletion, recipient list display, parameter description update, explanation text default update
- [ ] Phase 5 — address ownership: refuse confirmation of addresses owned elsewhere, release extras when an address becomes a main address (email change, member creation paths), migration for existing duplicates; `ExtraEmailMailingListManager` becomes `MailingListUnsubscriber` with the main address / `ExternalRecipient` check; recipient list without the "added first" rule
- [ ] Phase 6 — management link: signing service + validity parameter, `NewsletterManagementLinkProvider` becomes `SubscriptionManagementLinkProvider` by address (absolute profile URL, overrides for dynamic tokens, extras' override), trigger + draft, "Link senden" endpoint + button, public request page, "Abos verwalten" on the confirmed page, redirect of the old external link, page shell (expired state, redirect of main addresses, address header)
- [ ] Phase 7 — management page content: per-extra category state, shared category services extracted from `MemberMailCategoryDataApiView` (update-or-create, also for the member path; category selection, also for the snapshotter), address-based list services extracted from the member self-service views, API + island (extra part, external part, lists, removals), deletion of `ExternalRecipientManagementView` with its form and template, log entry, throttling (optional: decide at the beginning of the phase; if yes, it also covers the phase 6 request-link endpoint)
- [ ] Phase 8 — mailman subscriptions follow the member's email change
- [ ] Phase 9 — former members: `ActiveMemberProvider` (move `MemberSegmentProvider.get_queryset_active_members` with its tests, add `get_former_members`, update callers), nightly unsubscription task + log entry, blocking new subscriptions (self-service, management page, admin views, snapshot), list unsubscription in `DeleteMemberApiView`
- [ ] Phase 10 — test data generation (extras with and without direct mails; registrations of extras with direct mails through `MemberExtraEmailRegistrationSnapshotter`)
- [ ] Phase 11 — docs (`docs/admins`, explanation text): `ALWAYS_ON` categories are optional for extras, the snapshot runs only on the first confirmation, switching direct mails on later gives no snapshot, one owner per address, the management link token
- [ ] Phase 12 — delete this plan file (`plans/member_extra_email_subscriptions_plan.md`)

## Deployment and migration

The whole plan is implemented before deploying. Phase 1 alone would stop category copies to extras before phase 3 gives them their own registrations.

Migration `tapir_mail` 0053 replaces the former `internal_recipient_id` string of `InternalRecipientCategoryRegistration` with the foreign keys, linking existing rows to their member and deleting rows without one and older duplicates.

Existing extras get `receives_direct_mails=True`, but no registrations. Without a backfill, they would lose category mails they get today as copies, or fall back to the category defaults. A data migration (phase 3) backfills the categories, using historical models only:
- For each confirmed `MemberExtraEmail` and each `MailCategory` with a non-empty `dynamic_segment_name`: one `InternalRecipientCategoryRegistration(member_extra_email=extra, is_registered=<member's state>)`, via `bulk_create`.
- Member's state, as in `InternalRecipientManager.is_member_registered_to_mail_category`: `True` for `ALWAYS_ON`, else the member's own registration row if any, else `mode == OPTIONAL_DEFAULT_ON`.
- No segment membership check: it would need live segment code. A row for a category whose segment doesn't contain the member has no effect until the member joins it.
- Runs after `tapir_mail` 0053 (foreign keys).

No list backfill: no production instance uses mailman. Existing extras join lists through the management page.

The ownership migration (phase 5) runs after the backfill:
- Confirmed extras whose address is a member's main address are reset to unconfirmed.
- Among confirmed extras sharing an address, the one with the oldest `confirmed_on` is kept; the others are reset to unconfirmed.
- Reset extras lose their category registrations, backfilled ones included, so a later confirmation snapshots again without hitting the unique constraints. Their members are not notified.

Migrations run in the web container's start command before gunicorn (infra repo). Where `celery` waits for `service_healthy`, the backfill is in place before any mail is sent with the new code. Where it only waits for `service_started`, a dispatch during the migration fails on the missing column and is retried; no mail goes to the wrong addresses.
