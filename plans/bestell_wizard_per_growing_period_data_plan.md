# Plan: BestellWizard data per growing period and one order evaluation request (support ticket LEM#267)

## Problem

`BestellWizardBaseDataApiView.get` (`tapir/bestell_wizard/views.py:530`) computes `earliest_contract_start_date` from `available_growing_periods[0]` and uses it for:

- `product_ids_that_are_already_at_capacity`, `product_type_ids_that_are_already_at_capacity` → "(nur Warteliste-Eintrag möglich)" badge in Step4B
- `pickup_locations` (active filter at that date)
- `pickup_locations[].current_delivery_charge` (serializer context `reference_date_for_delivery_charge`)
- `solidarity_contribution_minimum`

When the user picks the second growing period in Step3B, all of these stay computed for the first one.

`PublicProductSerializer.get_price` and `PublicProductTypeSerializer.get_tax_rate` (`tapir/products/serializers.py`) always use today, also inside `growing_period_choices[].product_types`. `BestellWizardMobile.tsx` corrects prices with a separate request (`updateProductPrices` → `product_prices`) that mutates `settings.productTypes`; `BestellWizardProductType.tsx` doesn't, so it always shows today's prices.

Every cart change fires up to four requests, each rebuilding the order and the contract start date. Only the capacity check aborts outdated requests, so the others can apply stale results after fast clicks:

| Request | Used by |
|---|---|
| `bestell_wizard_capacity_check` | BestellWizardMobile, BestellWizardProductType |
| `pickup_location_capacity_check` | BestellWizardMobile, BestellWizardProductType, PickupLocationChangeModal |
| `bestell_wizard_delivery_dates` | BestellWizardMobile, BestellWizardProductType (`waiting_list_entry_id` never sent) |
| `minimum_number_of_shares` | BestellWizardMobile only (also once on load, with an empty cart) |

The minimum number of shares depends on `productTypesInWaitingList`, which the frontend derives from the capacity results and the selected pickup locations. The current effect doesn't depend on `productTypesInWaitingList`, so it can compute with a stale set.

## Target data flow

- **Base data, loaded once:** global settings, plus everything that depends only on the growing period, attached to each entry of `growing_period_choices`: product types with prices and tax rates, at-capacity lists, pickup locations with delivery charges, solidarity minimum. All at that period's contract start date.
- **`settings` in the frontend:** derived with `useMemo` from the loaded base settings and the selected period. `settings.productTypes` and `settings.pickupLocations` *are* the selected period's objects, so every object comparison in the wizard sees one set of objects per period.
- **Order evaluation, per cart change:** one request returning only what depends on the cart.
- **Minimum number of shares:** computed in the frontend from per-product `min_coop_shares`, since it depends on the waiting list set the frontend derives.

Delivered in two PRs. PR 1 fixes LEM#267 and can be deployed on its own. Each step below is one reviewable commit that leaves the app working: backend additions come before the frontend switch, removals come last.

## PR 1: base data per growing period

### Step 1.1: price and tax rate at a reference date (backend)

- `PublicProductSerializer.get_price` and `PublicProductTypeSerializer.get_tax_rate` (`tapir/products/serializers.py`): use `self.context.get("reference_date")`, falling back to today. Other users (`tapir/subscriptions/serializers.py`, `tapir/waiting_list/serializers.py`) don't pass it and keep today.
- Tests: price and tax rate at the context `reference_date`, today without it.
- No API change.

### Step 1.2: at-capacity lists as a service (backend)

- Move `build_product_ids_that_are_already_at_capacity` and `build_product_type_ids_that_are_already_at_capacity` out of `BestellWizardBaseDataApiView` into `tapir/bestell_wizard/services/already_at_capacity_provider.py`; the view calls the service.
- Move their tests along.
- Pure refactoring, no API change.

### Step 1.3: per-period data on the growing period choices (backend, additive)

- `PublicGrowingPeriodSerializer` (`tapir/deliveries/serializers.py:62`), only used by the base data response:
  - `get_contract_start_date`: use `self.context["cache"]` instead of `cache={}`.
  - `get_product_types`: pass `{**self.context, "reference_date": <contract start date>}`.
  - New fields, at the period's contract start date:
    - `product_type_ids_that_are_already_at_capacity: list[str]`
    - `product_ids_that_are_already_at_capacity: list[str]`
    - `pickup_locations`: `PublicPickupLocationSerializer(many=True)` with `reference_date_for_delivery_charge` = contract start date in its context
    - `solidarity_contribution_minimum: float | None`
- The top-level fields stay for now, so the current frontend keeps working.
- Regenerate `schema.yml` and the API client.
- Tests: two periods, first full and second with free capacity, price changing between the two contract start dates → each period gets its own at-capacity lists and prices; pickup locations and delivery charge at the period's contract start date.

### Step 1.4: frontend settings derived from the selected period (the LEM#267 fix)

- `BestellWizardSettings` keeps `productTypes`, `pickupLocations`, `productTypeIdsThatAreAlreadyAtCapacity`, `productIdsThatAreAlreadyAtCapacity`, `solidarityContributionMinimum`, so their consumers stay unchanged.
- New `src_frontend/bestell_wizard/utils/applyGrowingPeriod.ts`: `(settings, growingPeriod | undefined) => settings`, returning a new settings object whose five fields above are taken as-is (same object references) from `growingPeriod`. Returns `settings` unchanged when `growingPeriod` is undefined.
- `buildSettings`: fill the five fields from `growingPeriodChoices[0]` via `applyGrowingPeriod` instead of the top-level fields, so the coop shares and association membership wizards keep working unchanged. Drop the `sortProductTypes` call: the backend already sorts each period's product types, and it would sort the period's array in place.
- `BestellWizardMobile.tsx` and `BestellWizardProductType.tsx`:
  - Rename the state to `baseSettings`; `const settings = useMemo(() => applyGrowingPeriod(baseSettings, selectedGrowingPeriod), [baseSettings, selectedGrowingPeriod])`.
  - `updateWaitingList` effect: add `settings` to the dependencies, so `productTypesInWaitingList` holds the new period's objects.
  - `BestellWizardMobile.tsx`, waiting list entry load: filter out product type wishes that `getProductTypeByProductId` doesn't find in the first period, instead of asserting with `!`.
- `Step3ProductTypesChoice.tsx`: `selectedGrowingPeriod?.productTypes ?? settings.productTypes` → `settings.productTypes`.
- Delete `src_frontend/utils/updateProductPrices.ts` and the `productPricesController` state.
- Check: select 2027 in Step3B → no waiting list badge in Step4B, 2027 prices (M: 77.33 €). Select 2026 → badge, 2026 prices (M: 70.30 €). Same in the member profile product type wizard. Coop shares and association membership wizards still load.

### Step 1.5: period change handling (frontend)

- New shared helper `src_frontend/bestell_wizard/utils/onGrowingPeriodSelected.ts` (takes the setters), passed to `Step3BGrowingPeriodChoice` instead of `setSelectedGrowingPeriod` in both wizards. Runs only on a user choice, not on the initial selection (which would wipe the pickup locations restored from a waiting list entry). Step3B isn't shown in the waiting list entry flow, so that flow never reaches it.
  - `setSelectedGrowingPeriod(growingPeriod)`
  - `setSelectedPickupLocations([])` (the chosen locations may not be active in the new period)
  - rebuild the cart: `{...buildEmptyShoppingCart(growingPeriod.productTypes), ...<quantities of the products still in the period>}` (Step4B expects a key for every product)
- `BestellWizardMobile.tsx`: `contractStartDate` becomes `useMemo` over `selectedGrowingPeriod` instead of state set in the `[selectedGrowingPeriod]` effect.
- Stale responses, `checkPickupLocationCapacities`: so a response arriving after a period change can't set the previous period's pickup location objects, use an `ignore` flag set in the calling effect's cleanup (`let ignore = false; … return () => { ignore = true; }`), passed to the helper as `isIgnored: () => boolean`. Results and the loading flag are only set when not ignored. `PickupLocationChangeModal` does the same in its effect. `updateProductsAndProductTypesOverCapacity` keeps its state-held `AbortController` until PR 2 replaces it.
- Check: order, go to the pickup location step, go back and switch period → pickup location selection cleared, cart and summary consistent. Confirm a waiting list entry with pickup location wishes through the BestellWizard → wishes still selected.

### Step 1.6: remove the old fields and the prices endpoint (backend)

- `BestellWizardBaseDataResponseSerializer` / `BestellWizardBaseDataApiView.get`: remove `product_types`, `pickup_locations`, `solidarity_contribution_minimum`, both `*_already_at_capacity` fields, `earliest_contract_start_date` and the `reference_date_for_delivery_charge` context.
- Delete `PublicProductPricesApiView`, its URL (`api/product_prices`) and `PublicProductPricesResponseSerializer`.
- Regenerate `schema.yml` and the API client; the frontend must still compile.
- Tests: update the `BestellWizardBaseDataApiView` tests checking the removed fields; delete the prices endpoint tests.

## PR 2: order evaluation endpoint

### Step 2.1: pickup location capacity as a service (backend)

- Extract the capacity logic of `PickupLocationCapacityCheckApiView` into a service; the view calls it.
- Move its tests along.
- Pure refactoring, no API change.

### Step 2.2: order evaluation endpoint (backend, additive)

- New `BestellWizardOrderEvaluationApiView`, `POST bestell_wizard/api/order_evaluation`:
  - Request: `shopping_cart`, `growing_period_id` (required).
  - Builds the order and the period's contract start date once, shares one cache.
  - Response:
    - `ids_of_product_types_over_capacity`, `ids_of_products_over_capacity` (logic of `BestellWizardCapacityCheckApiView`)
    - `pickup_location_ids_with_enough_capacity_for_order` (service from step 2.1)
    - `delivery_date_by_pickup_location_id_and_product_type_id` (logic of `BestellWizardDeliveryDatesForOrderApiView` without the waiting list entry branch)
- Regenerate `schema.yml` and the API client.
- Tests: port the tests of `BestellWizardCapacityCheckApiView` and `BestellWizardDeliveryDatesForOrderApiView`; one test per response field.

### Step 2.3: one evaluation request in the wizards (frontend)

- New `src_frontend/bestell_wizard/utils/evaluateOrder.ts`, replacing `updateProductsAndProductTypesOverCapacity`, `fetchFirstDeliveryDates` and the wizard use of `checkPickupLocationCapacities` (`PickupLocationChangeModal` keeps using it): one request, one loading flag; sets the over-capacity lists, `pickupLocationsWithCapacityFull` and the first delivery dates. Stale responses are dropped with the same `ignore` flag pattern as in step 1.5.
- `BestellWizardMobile.tsx` and `BestellWizardProductType.tsx`: one `[shoppingCart, selectedGrowingPeriod]` effect calling `evaluateOrder`, replacing the three effects.
  - Empty cart: no request; reset the results to empty, so results of an earlier non-empty cart don't stay (a running request is ignored through the effect cleanup).
  - `BestellWizardMobile.tsx`, waiting list entry flow: request as usual, but ignore the two over-capacity lists (as today, where only the capacity check is skipped).
- Delete `updateProductsAndProductTypesOverCapacity.ts`, `fetchFirstDeliveryDates.ts` and the `checkingCapacitiesController` state.
- Check: click + / − quickly in Step4B → one request per change in the network tab, badges match the final cart. Delivery dates and pickup location capacities still shown, also in the waiting list entry flow.

### Step 2.4: minimum number of shares in the frontend

- Backend: `PublicProductSerializer`: add `min_coop_shares`. Base data: add `coop_min_shares` (parameter `COOP_MIN_SHARES`, 0 if the legal status isn't cooperative, as in `MinimumNumberOfSharesValidator`). Regenerate `schema.yml` and the API client.
- Frontend, `BestellWizardMobile.tsx`: `useMemo` over `[shoppingCart, productTypesInWaitingList, settings]`: `max(coopMinShares, Σ minCoopShares × quantity)` over the products not in the waiting list. An effect on the result sets `selectedNumberOfCoopShares`, as `updateMinimumNumberOfShares` does today. Delete `updateMinimumNumberOfShares.ts` and the initial `minimum_number_of_shares` request.
- Check: BestellWizard with a coop setup: minimum number of shares follows the cart and drops when a product type goes to the waiting list.

### Step 2.5: remove the replaced endpoints (backend)

- Delete `BestellWizardCapacityCheckApiView`, `BestellWizardDeliveryDatesForOrderApiView` (incl. `get_reference_date`, `get_relevant_product_type_ids`) and `MinimumNumberOfSharesApiView`, their URLs, serializers and tests. `MinimumNumberOfSharesValidator` stays for the order validation. Keep `PickupLocationCapacityCheckApiView` for `PickupLocationChangeModal`.
- Regenerate `schema.yml` and the API client; the frontend must still compile.
- Check: `PickupLocationChangeModal` still works.

### Step 2.6: delete this plan file

- Delete `plans/bestell_wizard_per_growing_period_data_plan.md`.

## Out of scope

- The member profile wizard checks capacities with `member_id=None`, ignoring the member's own current subscription. Separate ticket.
