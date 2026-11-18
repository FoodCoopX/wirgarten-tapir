# Plan: partial months pro rata by delivery dates (#1387)

Issue: #1387 "NEU: Teilmonate anteilig nach Lieferterminen abrechnen". Related: #1328 (joker credit value, whose formula this replaces).

## Progress
Tick a box right after finishing the step. Each phase writes and updates the unit tests for the code it changes (see "Tests"); Phase 7 adds the cross-cutting scenarios.

- [x] Phase 1 — cutoff parameter
- [x] Phase 2 — shared delivery counting + cutoff check
- [x] Phase 3 — subscription payments
- [x] Phase 4 — joker credit
- [x] Phase 5 — calculation explanation in the member profile payment list (payments and credits)
- [x] Phase 6 — texts (parameter descriptions, joker explanation)
- [x] Phase 7 — cross-cutting tests for criterion 9
- [x] Phase 8 — cleanup: remove `Payment.edited` (see "Cleanup (Phase 8)")
- [ ] Phase 9 — merge the migrations created by this plan (see "Migrations (Phase 9)")
- [ ] Phase 10 — documentation review (see "Documentation (Phase 10)")
- [ ] Phase 11 — delete this plan file (`plans/partial_month_pro_rata_plan.md`)

## Context

### User story
As a Solawi, a contract that starts or ends mid-month should cost exactly its share of the monthly fee, so that members don't pay twice on contract changes and billing is explainable.

### Status quo
`MonthPaymentBuilderSubscriptions.get_number_of_months_and_deliveries_to_pay` (`tapir/payments/services/month_payment_builder_subscriptions.py:203`):
- Fully covered month → full monthly price.
- Partially covered month → full monthly price if the subscription's own deliveries in the month reach `get_number_of_deliveries_for_full_month_price` (weekly 4, biweekly 2, every 4 weeks 1, custom 1, no delivery 0).
- Otherwise each delivery costs `DeliveryPriceCalculator.get_price_of_single_delivery_for_subscription` = monthly price × 12 ÷ weeks in year (× 2 biweekly, × 4 every 4 weeks).
- Weeks without delivery count (`check_for_weeks_without_delivery=False`).
- Custom delivery weeks (`force_price_per_delivery`) always pay per delivery.

Problem: on a mid-month change, old and new contract are computed separately. In months with 5 delivery dates the member pays one delivery twice.

Example October 2026 (5 Thursdays): 2 × box à 95 € until 26.10., from 27.10. 1 × 95 € + 1 × 65 €.
- today: 190.00 + 21.51 + 14.72 = **226.23 €**, more than without the change (190 €)
- pro rata: 4/5 × 190 + 1/5 × 160 = **184.00 €**

Simulation over all change days 2026 (95 € → 65 €), deviation from pro rata per month:
- weekly: −8.25 € to +20.72 €
- biweekly: −7.55 € to +39.43 €
- every 4 weeks: up to +80.00 € (in months with 1 date both contracts pay in full)

A contract split twice in a month without price change costs 86.04–138.02 € instead of 95 €, every 4 weeks 190 €.

Joker credit today (`JokerValueService`, from #1328): monthly price × 12 ÷ weeks in year (× cycle factor), solidarity contribution part analogous, plus pickup location delivery charge.

## Acceptance criteria
1. For months a contract doesn't fully cover: monthly price × (contract's delivery dates in month ÷ all delivery dates of the product type in month for the member). Fully covered months unchanged (share 1).
2. Delivery dates counted as today: delivery-free weeks count, member's pickup location history. Numerator and denominator use the same counting (`MonthlyDeliveryDateCounter.count_delivery_dates_in_month` with resp. without contract period).
   - Delivery-free weeks never reduce the denominator. Example: no delivery in KW 1 and 2 of January 2027, member's first delivery in KW 4 → 1/4 of January, not 1/2.
   - Consequence: a delivery-free week added at short notice in the running month changes neither numerator nor denominator.
3. 0 dates in the month → 0 € (no division by 0).
4. Custom delivery weeks (`force_price_per_delivery`) unchanged.
5. "Keine Lieferung": pro rata by days like the solidarity contribution (`get_amount_to_pay_for_contribution_within_month`). Applies from the cutoff date on; NO_DELIVERY gets its own branch and never reaches the delivery-date ratio (it has 0 delivery dates, so criterion 3 would make every partial month free).
6. Joker credit = value of the skipped delivery under the same rule as criterion 1, i.e. exactly what the member would pay for that one delivery.
   - Per contract: monthly price at the actual delivery date of the joker week (recomputed, see Phase 4) (incl. quantity resp. price override) ÷ all delivery dates of the product type in the joker's month for the member (same denominator as criteria 1 and 2).
   - Solidarity part: monthly contribution ÷ delivery dates of the product type selected in `JOKERS_SOLIDARITY_CONTRIBUTION_PRODUCT_TYPE` in the month.
   - Replaces yearly value × 12 ÷ weeks in year from #1328.
   - Unchanged: pickup location delivery charge, custom delivery weeks (price per delivery).
   - Cutoff date (criterion 7) applies: jokers in earlier months keep the old formula.
   - Explanation text e.g. "Kiste: 95,00 € monatlich ÷ 5 Liefertermine im Oktober = 19,00 €".
   - `DeliveryPriceCalculator.get_price_of_single_delivery_from_monthly_price` is not changed (still used before the cutoff).
   - Example 95 € box weekly: October 2026 (5 dates) 19.00 € instead of 21.51 € (member pays 95 − 19 = 76 € = 4/5 × 95 €, same as a contract ending one delivery earlier). November 2026 (4 dates) 23.75 € instead of 21.51 €. Jokers on all dates of a month sum to the monthly price (today October: 5 × 21.51 = 107.55 €).
7. Cutoff date: the new rule applies per month only from a cutoff date (config parameter, default 01.01.2028). Earlier months keep the old rule. Reason: with quarterly/yearly payment the whole period is recomputed; without a cutoff, already billed months would produce back-charges (e.g. 2 of 4 deliveries: old 43.02 €, new 47.50 €).
8. `MemberCreditCreator` and the sales export (`MonthlySalesSegmentProvider`) use `get_total_to_pay` and pick up the new rule without own changes.
9. Tests: all delivery cycles, months with 4 and 5 dates, change with and without price change, two changes in the same month (sum = 1 monthly fee), month with delivery-free weeks, pickup location change within the month, 0 dates, cutoff, yearly payment rhythm, trial period. Joker: all delivery cycles, months with 4 and 5 dates, solidarity part, joker before cutoff, jokers on all dates of a month (sum = monthly price).

### Out of scope
- Monthly price for multi-month payment periods is still taken on the first day of the period (price changes within a quarter ignored as before).
- Calculation explanation for delivery charge refund credits (`MonthPaymentBuilderDeliveryCharges.build_refund_credits_for_pickup_location_change`) and for credits created manually by admins (`MemberCreditCreateSerializer`, free-text comment).
- Entering/leaving mid-month costs 19.00 € or 23.75 € per week depending on the month instead of 21.51 € (yearly average). Intended: full months always cost the same, partial months their share. Same for joker credits.

### Outside the code
- Cutoff date and announcement to the Solawis to be agreed.
- Update the member FAQs of the instances if they explain partial months or the joker value.

## Design

### Rounding
No rounding per contract or per month. `MonthPaymentBuilderUtils.build_payment_for_contract_and_member` quantizes once (`total_to_pay - already_paid`). Compute `monthly_price * own_dates / total_dates` (multiply first) to keep the error far below a cent, so "two changes in one month = 1 monthly fee" holds after quantizing.
Joker credits are rounded to cents when saved as `MemberCredit`. "Jokers on all dates of a month = monthly price" therefore only holds exactly when the price divides by the number of dates (95 / 5, 95 / 4); with 3 dates the sum may differ by up to 1 cent per joker. Tests use divisible values; the sum test documents this.
Explanation lines (Phase 5) show amounts rounded to cents while the total is rounded once, so the displayed lines may not add up to the displayed total (e.g. 3 × 31,67 € = 95,01 € vs. total 95,00 €). Accepted.

### Shared delivery counting
New service `tapir/deliveries/services/monthly_delivery_date_counter.py`, `MonthlyDeliveryDateCounter.count_delivery_dates_in_month(member_id, product_type, first_of_month, contract_start, contract_end, cache)` with `contract_start`/`contract_end` optional (`None` = denominator). Logic moved from `MonthPaymentBuilderSubscriptions.get_number_of_deliveries_in_month` (pickup location history, `check_for_weeks_without_delivery=False`). Phase 7 changed it to loop over the weeks of the month with the pickup location valid on each week's Monday, like `MemberSpecificDeliveryDayCalculator`; before, the location valid on the previous delivery date decided the next date, so after a location change the first date came from the old location. Lives in `deliveries` so `JokerValueService` doesn't depend on `payments`. Results go through the cache: the denominator is requested for every subscription of a member and product type, and for every joker.
`get_number_of_deliveries_in_month` is removed and its tests moved (done in Phase 2; `get_number_of_months_and_deliveries_to_pay` calls the counter until Phase 3 replaces it).

### Cutoff
- New key `ParameterKeys.PAYMENT_PARTIAL_MONTH_PROPORTIONAL_START_DATE`, defined in `parameter_definitions_payments.py`, DATE, default 01.01.2028, validator `validate_date_is_first_of_month`. A month uses the new rule iff its first day ≥ cutoff.
- New service `tapir/deliveries/services/partial_month_calculation_mode_decider.py`, `PartialMonthCalculationModeDecider.is_proportional_mode_active(first_of_month, cache)`, used by payments and jokers.

### Payments (Phase 3)
Replace `get_number_of_months_and_deliveries_to_pay` (returns two ints, can't express a fraction) by a per-month function `build_calculation_part_for_subscription_within_month(subscription, first_of_month, monthly_price, price_of_single_delivery, cache) -> PaymentCalculationPart | None` (amount + explanation, analogous to `JokerCreditValuePart`; dataclass in `tapir/payments/dataclasses.py`; `None` if the subscription doesn't overlap the month), so the amount charged and the formula shown in Phase 5 come from the same code. Each branch below builds its own explanation, old rule included. `get_calculation_parts_for_subscription_within_range` loops over months and collects the parts; monthly price and single delivery price are still taken at `range_start` (out-of-scope point 1).

Per month, in this order:
1. Subscription doesn't overlap the month → `None`.
2. `force_price_per_delivery` → own dates × price per delivery (criterion 4).
3. Fully covered → monthly price.
4. NO_DELIVERY and proportional mode active → monthly price × days covered ÷ days in month, same ratio as `MonthPaymentBuilderSolidarityContributions.get_amount_to_pay_for_contribution_within_month` (shared helper `MonthPaymentBuilderUtils.get_number_of_days_covered_in_month`).
5. Proportional mode active → total dates = 0 ? 0 : monthly price × own dates ÷ total dates (criteria 1–3).
6. Else old rule: threshold (`should_pay_full_month_price`) → monthly price, otherwise own dates × price per delivery.

This also removes the latent infinite loop at `month_payment_builder_subscriptions.py:213` (`continue` without advancing `current_month`; unreachable today because callers pre-filter).
`MemberCreditCreator`, `MonthlySalesSegmentProvider`: amounts change without own changes (criterion 8); covered by existing tests. `MemberCreditCreator` comments are extended in Phase 5.

### Joker (Phase 4)
`JokerValueService`:
- `_get_subscription_part`: custom cycle unchanged. Proportional mode active for the joker month → `SubscriptionPriceCalculator.get_monthly_price(subscription, joker_date)` ÷ total delivery dates of the product type in that month (0 dates → 0); else old path.
- `_get_solidarity_contribution_part`: same, denominator from the product type selected in `JOKERS_SOLIDARITY_CONTRIBUTION_PRODUCT_TYPE`.
- `_get_delivery_charge_part`: unchanged.
- The whole credit calculation uses the actual delivery date, recomputed at evaluation time, instead of `joker.date`: subscription selection (`get_subscriptions_that_get_delivered_in_week` → `get_active_subscriptions`), monthly price, solidarity contribution, delivery charge, the month for the denominator and the cutoff check. Otherwise a contract starting on 01.10 would be missed for a joker stored as 30.09. Recomputation: `MemberSpecificDeliveryDayCalculator.get_specific_delivery_date(member_id, get_next_delivery_date(get_monday(joker_date)))`. `joker.date` is the member-specific pickup date at the time the joker was used and becomes stale if the member later switches to a pickup location with another weekday; in a week spanning two months (old location Wed 30.09.2026, new location Thu 01.10.2026) it would point to the wrong month. The recomputation uses the pickup location history, like the delivery date counting. The credit is created at the joker cancellation deadline, so later location changes don't affect it.
- New public `JokerValueService.get_actual_delivery_date(member_id, joker_date, cache)`. `get_joker_credit_value_parts` calls it first and passes the result on to all parts. `JokerCreditCreator._build_credit_for_joker` uses it instead of its own identical computation.
- New `_build_proportional_part(name, monthly_amount, member_id, product_type, delivery_date, cache)`, shared by the subscription and solidarity parts, and `_build_proportional_calculation(monthly_amount, number_of_dates, month)` → "95,00 € monatlich ÷ 5 Liefertermine im Oktober". `monthly_amount` is `get_monthly_price` (quantity and price override included), so no "× N Anteile" suffix; instead the name shows the quantity, e.g. "Kiste (2 Anteile): 190,00 € monatlich ÷ 5 Liefertermine im Oktober = 38,00 €". With price override: "Kiste (Sonderpreis): …". `_build_monthly_to_delivery_calculation` stays for jokers before the cutoff.
- `get_price_of_single_delivery_from_monthly_price` unchanged.
- Callers `IntendedUsePatternExpander`, `MemberColumnProvider`: no change.

### Calculation explanation in the member profile (Phase 5)
Shown in `FuturePaymentsModal.tsx` (member profile), visible to everyone who can see the payment list: admins and, with `MEMBERS_CAN_SEE_OWN_PAYMENTS`, the member themselves. All texts are therefore written for members.

Payments (subscription and solidarity contribution payment types):
- The explanation is computed when the payment is built and stored on the payment: new field `Payment.calculation_explanation` (text, empty for other payment types and for payments created before the deploy). Recomputing persisted payments later can't reproduce the original numbers (stored range ≠ rhythm period in trials, later correction payments would count as "already paid").
- `MonthPaymentBuilderSubscriptions.get_calculation_parts(range_start, range_end, contracts, cache) -> list[PaymentCalculationPart]`: subscriptions overlapping the range, sorted by start date, then per subscription the per-month parts of Phase 3 (`get_calculation_parts_for_subscription_within_range`). `get_total_to_pay` sums them.
- `MonthPaymentBuilderSolidarityContributions.get_calculation_parts(...)` the same, per month `build_calculation_part_for_contribution_within_month` (full month: "Oktober 2026, Solidarbeitrag: 10,00 € monatlich (voller Monat)"; partial month by days: "Oktober 2026, Solidarbeitrag: 10,00 € × 12 von 31 Tagen = 3,87 €"; amounts still rounded per month as before).
- `MonthPaymentBuilderUtils.build_payment_for_contract_and_member` takes either `total_to_pay_function` (delivery charges, association membership: no explanation) or `calculation_parts_function` (subscriptions, solidarity contributions). With parts, `build_calculation_explanation` writes the lines, "Summe", and if something was already paid "Bereits bezahlt" and "Zu zahlen".
- `PaymentSerializer` uses `fields = "__all__"`, so the field reaches the frontend without serializer changes.

Credits:
- Joker credits already store the calculation in `comment` (`JokerValueService.build_explanation`).
- `MemberCreditCreator`: `get_amount_to_credit` becomes `get_credit_calculation -> CreditCalculation(amount, explanation)`; the explanation ("Berechnung der Gutschrift:", parts, Summe, Bereits bezahlt, Gutschrift) is appended to the credit comment. The admin-written comments ("Produkt-Anteil vom Admin … reduziert") stay as first line. The solidarity contribution path gets the same treatment from `MonthPaymentBuilderSolidarityContributions` (by days).
- `FuturePaymentsModal.buildCredit` shows `credit.comment` (line breaks preserved). `comment` is already in `MemberCreditSerializer`.

Frontend: `CalculationExplanation.tsx` shows the text below the amount, collapsed by default ("Berechnung anzeigen"), in `PaymentComponent` and `FuturePaymentsModal.buildCredit`. Schema and API client regenerated for the new `Payment` field.

### Texts (Phase 6)
- `parameter_definitions_jokers.py`: the description of `JOKERS_SOLIDARITY_CONTRIBUTION_PRODUCT_TYPE` names the old formula; mention both formulas and the cutoff.
- Cutoff parameter description: the new formula in one sentence (partial months cost monthly price × own delivery dates ÷ all delivery dates of the month; joker credit = monthly price ÷ delivery dates of the month) and that months before the cutoff keep the old formula.
- Member FAQs live in the instances, not in the repo: list them in the PR description as follow-up.

## Tests
One class per file, one file per method, `TapirUnitTest` where no DB is needed. Each phase writes the tests for its own code; tests of removed methods are removed in the phase that removes the method. Phase 7 covers the cross-cutting scenarios of criterion 9 marked below.

Phase 2, `tapir/deliveries/tests/services/`:
- `monthly_delivery_date_counter/test_count_delivery_dates_in_month.py`: with and without contract range, delivery-free weeks count, pickup location change within the month, 0 dates, all cycles.
- `partial_month_calculation_mode_decider/test_is_proportional_mode_active.py`: month before, month equal to, month after the cutoff.

Phase 3, `tapir/payments/tests/services/month_payment_builder_subscriptions/`:
- `test_build_calculation_part_for_subscription_within_month.py` (replaces `test_get_number_of_months_and_deliveries_to_pay.py`): each branch; weekly, biweekly, every 4 weeks, custom, no delivery; months with 4 and 5 dates; 0 dates; cutoff before/after the month.
- Phase 7: `test_get_total_to_pay_integration.py` (new, DB; `test_get_total_to_pay.py` stays a unit test): issue example October 2026 = 184.00 €; two changes without price change in one month = 1 monthly fee (also covers a single change, e.g. renewal into a growing period starting mid-month); January 2027 with KW 1–2 delivery-free, start KW 4 = 1/4; pickup location change within the month; yearly rhythm spanning the cutoff (months before old rule, after new).
- Trial period: no own test. Trial only shifts the target month and forces the monthly rhythm (covered by `test_build_payments_for_subscriptions_in_trial.py`, which asserts `calculation_parts_function=get_calculation_parts`); the amount comes from `get_calculation_parts`, covered by `test_get_total_to_pay_integration.py`.
- Remove the tests of `get_number_of_months_and_deliveries_to_pay`.

Phase 4, `tapir/deliveries/tests/services/joker_value_service/`:
- `test_get_subscription_part.py` (extend): all cycles, October 2026 = 19.00 €, November 2026 = 23.75 €, before cutoff = 21.51 €, quantity and price override, explanation text (quantity shown once, in the name).
- `test_get_solidarity_contribution_part.py` (extend): denominator from the selected product type, before/after cutoff.
- `test_get_joker_credit_value_for_single_joker.py` (extend): Phase 7: jokers on all dates of October 2026 sum to 95 €. Phase 4: subscription starting 01.10.2026 is included for a joker stored as 30.09.2026 after a switch to a Thursday location; joker in the week of Mon 28.09.2026 used at a Wednesday location (`joker.date` 30.09.2026), member then switches to a Thursday location → October denominator and October cutoff check.
- `test_get_actual_delivery_date.py` (new): call test (Monday of the joker week → next delivery date → member-specific date); the location scenarios are covered in `test_get_joker_credit_value_for_single_joker.py`.
- `test_build_proportional_calculation.py` (new).

Phase 5:
- `month_payment_builder_subscriptions/`: `test_get_calculation_parts.py` (new), `test_get_calculation_parts_for_subscription_within_range.py` (renamed), `test_get_total_to_pay.py` (sums the parts).
- `month_payment_builder_solidarity_contributions/`: `test_get_calculation_parts.py` (new), `test_get_calculation_parts_for_single_contribution_within_range.py` (renamed, explanation texts), `test_get_total_to_pay.py` (sums the parts).
- `month_payment_builder_utils/`: `test_build_calculation_explanation.py` (new), `test_build_payment_for_contract_and_member.py` (explanation stored on the payment).
- `member_credit_creator/`: `test_get_credit_calculation.py` (renamed, explanation), `test_build_explanation.py` (new), `test_create_member_credit_if_necessary.py` (comment = admin comment + explanation).
- `tapir/payments/tests/views/test_get_future_member_payments_api_view.py` (extend): generated payments carry the explanation.

## Cleanup (Phase 8)
`Payment.edited` (`tapir/wirgarten/models.py:735`) is dead: the admin UI for editing payments was removed in e39e5963 (2025-09-01), nothing sets or reads the field since.
- Remove the field from `Payment` and generate the migration with `makemigrations`.
- `PaymentSerializer` uses `fields = "__all__"`, so the field disappears from the API: regenerate `schema.yml` and the API client (`src_frontend/api-client/models/Payment.ts`).
- Grep again for `edited` (Python, templates, frontend, exports) before removing; at the time of writing there is no other usage.

## Migrations (Phase 9)
Merge all migrations created on this branch into as few as possible, ideally one per app:
- List them with `git diff --name-only master... -- '*/migrations/*'`.
- Auto-generated migrations of the same app: delete them and run `makemigrations` again to get a single one.
- Hand-written migrations (e.g. data migrations): fold their operations into the regenerated migration if the order of operations allows it, otherwise keep them separate.
- Check that `makemigrations --check` reports no changes and the tests still pass.

## Documentation (Phase 10)
- Review the existing documentation (`docs/admins/`, in-app texts) for anything describing partial months, per-delivery prices or the joker value, and update it.
- Consider adding or updating help buttons (`src_frontend/components/TapirHelpButton.tsx`) where members or admins see the affected amounts, e.g. joker list (`DeliveryListCard.tsx`), subscription changes, payment overviews.
- Consider a dedicated page, e.g. `docs/admins/payments/partial_months_and_joker_credits.md`: delivery-date fraction with the October 2026 example, delivery-free weeks counting, "Keine Lieferung" by days, joker formula, cutoff parameter and what happens to earlier months.

## Files
- `tapir/wirgarten/parameter_keys.py`, `tapir/wirgarten/parameter_definitions/parameter_definitions_payments.py`, `parameter_definitions_jokers.py`
- new `tapir/deliveries/services/monthly_delivery_date_counter.py`, new `tapir/deliveries/services/partial_month_calculation_mode_decider.py`
- `tapir/payments/dataclasses.py`, `tapir/payments/services/month_payment_builder_subscriptions.py`, `tapir/payments/services/month_payment_builder_solidarity_contributions.py` (shared days ratio), `tapir/payments/services/month_payment_builder_utils.py`
- `tapir/deliveries/services/joker_value_service.py`, `tapir/payments/services/joker_credit_creator.py`
- `tapir/wirgarten/models.py` + migrations (`Payment.calculation_explanation` in Phase 5, `Payment.edited` removal in Phase 8)
- `tapir/payments/services/member_credit_creator.py`, `schema.yml`, `src_frontend/api-client`, `src_frontend/member_profile/future_payments/` (`FuturePaymentsModal.tsx`, `PaymentComponent.tsx`, new `CalculationExplanation.tsx`)
- `docs/` (Phase 10)
- tests listed above
