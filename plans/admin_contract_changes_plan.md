# Plan: admin contract actions on the contract list (#1037, variant 2)

## Goal

Two new icons in the action bar of `/tapir/contracts` (`subscription_filter.html`), left of the existing ones:

- **Anteilsgröße ändern**: `edit_note` — "Anteilsgröße zu einem bestimmten Datum verändern". Implemented first.
- **Vertrag hinzufügen**: `post_add` — "Vertrag hinzufügen". Reuses most of "Anteilsgröße ändern".

Reference: prototype on `codex/issue-1037-admin-contract-prototype-v2` (#1347), screenshots in
`docs/prototypes/issue-1037/v2/`. The prototype is plain JS + a Django JSON view; it is only a UI reference. The
implementation is React + DRF like the other buttons of that bar (`SubscriptionChangeDatesButton` etc.).

## Anteilsgröße ändern

### Flow (one modal, three steps, content swapped in place)

1. **Mitglied & Anteil**
   - Member search: number, first name, last name, any combination. Help button next to the field. If a contract row
     is selected in the list (`contract` URL parameter), its member is preselected and the search is skipped; "Anderes
     Mitglied" goes back to the search.
   - After selection: list of the member's subscriptions, **one row per unit** (a subscription with quantity 3 gives
     3 selectable rows). Product type · product, dates, badge "Laufend / geplant" / "Gekündigt" / "Beendet".
     Cancelled or ended subscriptions are greyed out with "Dieser Vertrag ist bereits gekündigt und kann daher nicht
     bearbeitet werden".
   - Badge "Personalisierter Betrag" / "Beitragsbefreit" from `price_override` (no amount).
   - Status lines: pickup location, banking data, payment rhythm (check / cross).
2. **Anteilsgröße & Datum**
   - Product type locked, new product select (same type, not deleted, ≠ current product). No quantity field.
   - Start date, three options:
     - a) next possible start (`ContractStartDateCalculator.get_next_contract_start_date(today, apply_buffer_time=True)`),
     - b) a calendar week in the growing period of the selected subscription: year select, then week select showing
       the Monday; only Mondays ≥ today. Weeks before the next possible start are allowed (admin override) and marked
       with a hint that the buffer time is ignored. Weeks without delivery
       (`WeeksWithoutDeliveryService.is_delivery_cancelled_this_week`) are allowed and marked with a hint as well,
     - c) start of the next growing period.
     An option is disabled (with reason) if its date is outside the selected subscription's `[start_date, end_date]`,
     except option c for a subscription that ends at the end of the current period (change from next season).
     Growing periods are assumed to follow each other without gap; a gap (as at LEM) is a configuration error of the
     organisation and is not handled.
   - Live capacity check on every change (product, global, pickup location). Warning + "Weiter" disabled if not OK,
     as in screenshot `aendern-4`.
   - Right column: pickup location, payment rhythm, banking data. Since the member already has a subscription, all
     three are normally present; if one is missing, show the input (same as "Vertrag hinzufügen").
   - When banking data is entered: required checkbox "Ein unterschriebenes SEPA-Mandat liegt vor". Checked →
     `sepa_consent` set to now, as in the member-profile flow.
3. **Zusammenfassung**: Bisher → Neu, wirksam ab, Vertragsende, pickup location, payment rhythm, banking data, preview of
   the log entry. "Speichern" applies.
   - Warning if a subscription of the type has a `price_override`: the personalised price / exemption is removed, also
     for the unchanged units, and must be set again with the price button.
   - If next-period subscriptions of the type exist: they are replaced by renewals of the new subscriptions. The
     summary lists the next-period subscriptions before and after, so the admin sees when a different next-period
     choice of the member is overwritten.
   - Note that the member receives a confirmation mail.

### Backend

New files under `tapir/subscriptions/`:

- `views/admin_contract_changes.py`, permission `HasCoopManagePermission`:
  - `AdminContractChangeMemberDataApiView` (GET `member_id`): member summary + unit rows + status of pickup location /
    banking data / rhythm + the three date options (dates, enabled flag, reason).
  - `AdminContractChangeCheckApiView` (POST): runs the validator, returns `{ok, error}` + capacity flags. Used for the
    live check in step 2.
  - `AdminContractChangeApplyApiView` (POST): validates again, applies under `transaction.atomic()`.
  - Member search: reuse `MemberSearchService.filter_queryset` through a small search endpoint (or the existing member
    list API if it already supports `search`; check before adding one).
- `services/admin_size_change_order_builder.py`: builds the full `TapirOrder` of the product type at the change date from
  the member's subscriptions active at that date, minus 1 of the old product, plus 1 of the new one.
- `services/admin_size_change_validator.py` (`TapirCache` lookups, unit-testable):
  - subscription belongs to the member, not cancelled, `start_date ≤ date ≤ end_date`, or date = start of the next
    growing period and the subscription ends at the end of the current one,
  - date ≥ today and either a Monday or the start date of a growing period (period starts are rarely Mondays: 61–85 %
    of prod contracts start on the period start),
  - new product: same type, not deleted, different from the current one,
  - no other subscription of that product type active at the date is cancelled (applying would un-cancel it),
  - `OrderValidator.validate_order_general` on the built order (capacity, pickup location, single-subscription rules),
  - missing pickup location / rhythm / banking data provided (reuse `SubscriptionUpdateViewValidator.validate_banking_data`
    and `validate_pickup_location`); SEPA mandate checkbox checked when banking data is entered.
- Apply: reuse `ApplyTapirOrderManager.apply_order_single_product_type(contract_start_date=date,
  needs_admin_confirmation=False)`. It ends the current subscriptions of the type the day before, creates the new ones,
  keeps the trial period, writes the `SubscriptionChangeLogEntry` CANCELLED + ADDED entries ("alle Änderungen
  geloggt"). Then `MemberCreditCreator.create_member_credit_if_necessary`, as `SubscriptionUpdateViewChangeApplier`
  does. Pickup location / rhythm / banking data through the same setters as `SubscriptionUpdateViewChangeApplier`;
  extract its shared part instead of duplicating it.
- Created as confirmed (`needs_admin_confirmation=False`), not listed in "Verträge bestätigen".
- **The previous contract is always marked as cancelled** (`cancellation_ts` and `cancellation_admin_confirmed` set to
  now, change logged). For a change in the current period `cancel_or_delete_subscriptions` already does it. For a
  change from next season (option c on a current-period subscription) the end date stays, only the cancellation is
  set. Otherwise the renewal task would renew it next to the new contract, since `must_subscription_be_renewed` only
  looks for a next-period contract of the same product.
- `price_override` is dropped (decided): the new subscriptions get the standard price.
- **Change from next season** (option c on a current-period subscription): existing next-period subscriptions of the
  type are deleted (logged); the next-period order is the renewal of the current subscriptions of the type
  (`build_renewed_subscription`) with the swap applied (−1 old product, +1 new product). Capacity is checked at the
  next period start.
- **Next-period subscriptions** (change in the current period): `cancel_or_delete_subscriptions` deletes subscriptions
  of the type that start after the change date. When the member had non-cancelled subscriptions of the type in the
  next period:
  - renew each new current-period subscription with `AutomaticSubscriptionRenewalService.build_renewed_subscription`,
    the function used by the renewal task. Trial data, notice period and confirmation are set as a renewal sets them;
    a second `ApplyTapirOrderManager` call would treat them as a new order (new trial period, extra "added" log entry).
  - The admin's change takes precedence: if the member had a different next-period order (not a plain renewal of the
    current one), it is overwritten.
  - Validate capacity for the renewed order at the next period start as well.
  - Log the renewed subscriptions with a `SubscriptionChangeLogEntry` ADDED entry, since the deleted next-period
    subscriptions are part of the CANCELLED entry.
  - If the member had no next-period subscriptions of the type, nothing is created: the renewal task handles it later.
- **Mail**: always sent, once, with all new subscriptions (current + next period), through
  `ApplyTapirOrderManager.send_order_confirmation_mail` (contract change mail for "Anteilsgröße ändern", order or
  change mail for "Vertrag hinzufügen" depending on existing subscriptions).
- Serializers without validation; regenerate the API client (`regenerate-api-client` skill).

### Frontend

`src_frontend/subscription_list/`:

- `AdminContractChangeButton.tsx`, `AdminContractChangeModal.tsx` (step state machine), shared pieces reused by
  "Vertrag hinzufügen": `MemberSearchInput.tsx`, `ContractStartDateOptions.tsx` (year → week, Monday shown in the option),
  `MemberContractPrerequisitesCard.tsx` (pickup location / rhythm / banking data, turns green once filled).
- Register in `subscription_list_entry.tsx`, mount span in `subscription_filter.html`.
- Help texts via `TapirHelpButton`.
- After saving: toast + page reload so the list shows the new subscriptions.

### Tests

- Unit: order builder (quantity 1 and > 1, other products of the type kept), validator (each rule, `Factory.build`,
  cache filled through `TapirCache`; a period start that is not a Monday is accepted), date options service (buffer
  time hint, week-without-delivery hint, weeks of the selected subscription's period, period boundaries, ISO year
  change, period start not on a Monday).
- Applier (service tests): old subscription ends on `date - 1`, cancellation set; new subscriptions from `date`;
  quantity > 1 remainder; trial carried over; `price_override` dropped; created as confirmed (`auto_confirmed` set,
  not in the unconfirmed changes); credit created when prepaid; contract change mail sent once with all new
  subscriptions; log entries.
- Next-period (service tests): plain renewal replaced, different next-period order overwritten, no next-period
  subscriptions → nothing created, trial data as for a renewal, capacity checked at the next period start.
- Change from next season (service tests): previous contract keeps its end date and is marked as cancelled,
  next-period order = renewal with the swap, existing next-period subscriptions replaced, the renewal task doesn't
  renew the previous contract afterwards.
- Integration (API): permission denied for non-admins; validation or capacity error returns a message and writes
  nothing; successful apply.

## Vertrag hinzufügen

Same modal component, mode `new`:

1. Member search (shared).
2. Product type, product, quantity (integer ≥ 1), same date options (without the subscription-range restriction;
   options limited to the current and next growing period), prerequisites card with pickup location select (only
   locations with capacity for the order), rhythm and banking data if missing. Collapsible list of existing shares.
3. Summary + save.

Apply: order = existing subscriptions of the type at the date + the new product × quantity, through the same
`ApplyTapirOrderManager` path; same validator minus the subscription-specific rules. Same decisions as "Anteilsgröße
ändern": mail always sent, auto-confirmed, next-period subscriptions of the type replaced by renewals of the new ones,
`price_override` warning, SEPA mandate checkbox, preselected member.

## Decisions

1. **Mails**: always sent, no checkbox.
2. **`price_override`**: dropped on change, with a warning in the summary.
3. **Next-period subscriptions**: replaced by renewals of the new current-period subscriptions
   (`build_renewed_subscription`); the admin's change overrides any different next-period choice.
4. **Admin confirmation**: auto-confirmed.
5. **Buffer time**: any Monday ≥ today in option b, weeks inside the buffer marked with a hint.
6. **Previous contract**: always marked as cancelled, also for a change from next season.
7. **Banking data entered by the admin**: only with the checkbox "Ein unterschriebenes SEPA-Mandat liegt vor".
8. **Preselected member**: taken from the selected contract row, if any.

## Steps

Each step ends in a reviewable state, with its own tests, and is committed by the user before the next one starts.
Steps 1–2: test data. Steps 3–9: "Anteilsgröße ändern". Steps 10–11: "Vertrag hinzufügen". Steps 12–13: wrap-up.
"Anteilsgröße ändern" becomes visible only in step 9, so the work can be merged after any step.
Mark a step as done by checking its box (`- [x]`).

- [x] **1. Test data: sync with prod**: make all generated data plausible, not only the data relevant here. Base: the
  "Prod data reference" section and its list of differences with `populate`. Run `populate`, review the result through
  the UI and DB, and fix the generators (`tapir/utils/services/test_data_generation/`) where the data is implausible.
  Also check what the prod reference doesn't cover: date consistency (cancellations before end dates, log entries and
  payments matching the contracts), pickup location capacities not exceeded, required product types respected,
  payment rhythms and banking data consistent with contracts. List the findings first and agree on which to fix before
  changing the generators. No feature-specific data in this step.
  Benchmark: time `make populate` (same machine, 3 runs, median) before the first change and after the last one.
  The result must not be significantly slower; record both timings in the step's summary.
- [x] **2. Test data for this feature**: on top of step 1, a few members with quantity > 1 subscriptions, members
  without banking data / payment rhythm, personalised and exempt prices, in proportions that stay close to prod.
  Benchmark as in step 1, with the step 1 result as baseline.
- [x] **3. Refactor: shared contract prerequisites**: extract the pickup location / payment rhythm / banking data part
  of `SubscriptionUpdateViewChangeApplier` and `SubscriptionUpdateViewValidator` into a service used by the
  member-profile flow. No behaviour change; existing tests stay green and the extracted service gets its own unit tests.
- [ ] **4. Size change core**: `AdminSizeChangeOrderBuilder` + `AdminSizeChangeValidator` + an applier that calls
  `ApplyTapirOrderManager` for the change date, marks the previous contract as cancelled, creates the credit, sends the
  mail. Without next-period handling. Unit tests for builder and validator, service tests for the applier (end dates,
  cancellation, log entries, trial carried over, mail, quantity > 1 remainder, SEPA consent).
- [ ] **5. Next-period subscriptions**: change in the current period → renew the new current-period subscriptions with
  `AutomaticSubscriptionRenewalService.build_renewed_subscription` if next-period subscriptions of the type existed,
  overwriting any different next-period choice. Change from next season (option c) → previous contract cancelled with
  its end date kept, next-period order = renewal with the swap. Both: capacity at the next period start, log, single
  mail. Tests as listed in "Tests". Isolated because it is the trickiest rule.
- [ ] **6. Read endpoints**: member search, member data (unit rows, price badges, prerequisites status) and the date
  options service (a / b / c; Monday or growing period start, ≥ today; weeks of the selected subscription's period;
  buffer and week-without-delivery hints; subscription-range restriction with the option c exception). Regenerated API
  client.
- [ ] **7. Write endpoints**: check endpoint (live validation + capacity flags) and apply endpoint
  (`transaction.atomic()`). API tests: permission, validation error writes nothing, successful apply. Regenerated API
  client.
- [ ] **8. Frontend shared components**: `MemberSearchInput` (with preselected member from the `contract` URL
  parameter), `ContractStartDateOptions` (year → week), `MemberContractPrerequisitesCard` (with the SEPA mandate
  checkbox). Built for both icons, not mounted yet.
- [ ] **9. Frontend "Anteilsgröße ändern"**: button, modal with the three steps, live check, summary warnings (price
  override, next-period subscriptions, mail), toast + reload. Mounted in `subscription_filter.html`.
- [ ] **10. "Vertrag hinzufügen" backend**: order builder for an addition, validator variant (pickup location choice
  among locations with capacity), applier reusing steps 4/5, endpoints, tests, regenerated API client.
- [ ] **11. "Vertrag hinzufügen" frontend**: `new` mode of the modal (product type, product, quantity, pickup location
  select, collapsible existing shares), mounted next to "Anteilsgröße ändern".
- [ ] **12. Documentation review**: check `docs/` (mkdocs) for pages to update or add, e.g. an admin page under
  `docs/admins/` for both icons (dates, mail, price override, next-period subscriptions, SEPA mandate) and the effects
  on payments in `docs/admins/payments/`. Also check the help texts in the modals and the agent rules in
  `.agents/rules/`.
- [ ] **13. Delete this plan file** (`plans/admin_contract_changes_plan.md`).

## Prod data reference (read 2026-11-19, for step 1)

Aggregates from the contract and member lists of KGZ, HAL, LEM, SOS. "Current" = contracts of the current growing period.

| | KGZ | HAL | LEM | SOS |
|---|---|---|---|---|
| Legal form | coop | coop | GbR | e.V. |
| Growing period | 01.03–28.02 | 01.01–31.12 | 01.05–31.12, next 01.04–29.02 (gap: configuration error) | 01.08–31.03 |
| Members in list | 574 (479 coop members, 95 neither) | 200 (152 members, 26 exempt, 22 neither) | 56 | 139 |
| Current contracts / members with contracts | 322 / 264 | 147 / 147 | 54 / 54 | 162 / 135 |
| Product types | Gemüse, Obst, Apfelsaft | Ernteanteil only | Ernteanteil only | Gemüsekiste, Kuhpaket, Schafpaket |
| Members with 2+ product types | 55 of 264 | — | — | 24 of 135 |
| Several contracts of one type per member | 0 | 0 | 0 | 3 |
| Quantity > 1 | 2 (5 and 12, likely institutional) | 0 | 0 | 0 (1 among ended) |
| Start = period start | 74 % | 79 % | 61 % | 85 % |
| Other starts | Mondays only | Mondays only | Mondays only | Mondays only |
| End of active contracts | all at period end | all at period end | all at period end | all at period end |
| End of ended / cancelled contracts | Saturday | Sunday | Sunday | Sunday |
| Cancelled in current period | 43 (13 %) | 11 (7 %) | 0 | 3 (2 %) |
| In trial period | 44 | 5 | 0 | 7 |
| Trial manually disabled | 193 | 3 | 0 | 0 |
| `price_override` ≠ 0 / = 0 | 0 / 0 | 1 / 3 | 1 / 0 | 0 / 2 |
| Next-period contracts already created | no | yes (138) | yes (54) | no next period yet |
| Coop shares per member (coops) | 1 share 59 %, 0 → 17 %, 2 → 13 %, 3+ → 11 % | mixed amounts, 0 → 24 % | — | — |
| Members with 0 €/month revenue | 54 % | 26 % | — | — |

Not visible in lists (would need per-member pages, not read): payment rhythm distribution, missing banking data.

### Differences with `populate` (`user_generator.py`)

1. Contract starts are random dates; prod starts on the period start or on a Monday.
2. Current-period contracts are never cancelled; only past-period ones (25 %). Prod: 0–13 % cancelled in the current period,
   ending on a Sunday (KGZ Saturday).
3. No `price_override` at all; prod has a few personalised or zero prices.
4. `create_coop_shares_for_user`: `shares = max(1, min_shares)` overwrites the random extra shares, so nobody gets extra
   shares. Prod: ~25 % of coop members hold more than the minimum.
5. No renewals for the next period. On prod they come from the automatic renewal task
   (`AutomaticSubscriptionRenewalService`): a non-cancelled subscription is renewed once today is past its max
   cancellation date (`NoticePeriodManager.get_max_cancellation_date_subscription`), if
   `SUBSCRIPTION_AUTOMATIC_RENEWAL` is on and a next growing period exists. HAL and LEM are past that date, KGZ is not.
   Fix: call `AutomaticSubscriptionRenewalService.renew_subscriptions_if_necessary()` at the end of `populate` instead of
   creating renewals by hand, so next-period contracts exist only when the notice period is over. The generated
   previous → current period renewals follow the same rule (always past the deadline), so they can stay as they are.
   New orders that start in the next period (members joining for next season) are a separate case and stay.
6. Payment rhythm chosen among all choices, ignoring the allowed rhythms parameter (to verify).
7. No trial-disabled contracts; KGZ has many (likely from its migration).
8. Quantity > 1 at ~2 %: plausible; prod is lower, but the feature needs some.

## Out of scope

- Merging all contract actions into one management dialog (follow-up mentioned in #1347).
- Changing quantity in the size-change flow.
