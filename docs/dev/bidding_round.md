# Bidding round (Beitragsrunde)

The bidding round lets members submit a bid (monthly contribution) for harvest shares. After the
round ends, the operator locks an average bid and creates the matching subscriptions.

## Feature flags

Two parameters gate the feature (see `tapir/wirgarten/parameter_definitions/parameter_definitions_bidding_round.py`):

- `BIDDING_ROUND_ENABLED` – master switch. When off, **every** bidding-round page and API endpoint
  answers with `404` (enforced by `BiddingRoundFeatureFlagMixin` / `BiddingRoundFeaturePermission` in
  `tapir/bidding_round/permissions.py`).
- `BIDDING_ROUND_URL_ENABLED` – additionally gates the public, member-facing endpoints
  (`public_data`, `public_results`, `public_bids/capacity_check`, `member_bid`). Admin endpoints stay
  reachable so an operator can still configure the round.

## Lifecycle

`BiddingRoundService` (see `tapir/bidding_round/services/bidding_round_service.py`) owns the status
transitions:

`CONFIGURATION` → `ACTIVE` (`start_round`, one active round at a time) → `CLOSED` (`close_round`).
`reopen_round` and `delete_round` are blocked once `contracts_created_at` is set.

## Bidding

- Members both bid through `MemberBidView`; operators can enter/edit bids through the admin endpoints.
- `BidValidator` (`tapir/bidding_round/services/bid_validator.py`) validates round openness, product/round
  consistency, levels, the minimum amount and the quantity flag. Amounts are parsed defensively.
- `save_bid` / `save_admin_bid` run inside a transaction and lock the round row.
- `BIDDING_ROUND_BID_QUANTITY_ENABLED` is enforced server-side: when off, only `quantity == 1` is accepted.
- Pickup locations: when `BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED` is off, a submitted location is
  ignored and the member's own location is kept. The member's own location is always exposed through
  `current_pickup_location` (incl. yearly delivery charge), independently of that flag.
- Bids can no longer be changed once contracts have been created.

## Evaluation and contracts

- `BiddingRoundStatsService` builds the results, statistics, traffic-light position and financing
  projection.
- `BiddingRoundService.lock_average_bid` freezes the average bid (position, surcharge).
- `ContractCreator.create_contracts_from_bids` creates the subscriptions. It only sets
  `contracts_created_at` when at least one subscription was created, so a failed run can be retried.
  Existing non-cancelled subscriptions for the same product/season are replaced; the originals are
  snapshotted in `BiddingRoundReplacedSubscription` and restored by
  `BiddingRoundContractDeletionService.delete_contracts`.

## Tests

`make test-app APP=bidding_round`. The end-to-end demo data comes from
`tapir/utils/services/test_data_generation/bidding_round_generator.py`.
