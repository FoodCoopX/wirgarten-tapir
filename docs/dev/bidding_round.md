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

## Flow diagrams

### 1. Feature-flag gating (pages and API)

Every bidding-round page and API endpoint passes the same gate. `BiddingRoundFeatureFlagMixin` /
`BiddingRoundFeaturePermission` run before the view logic; the public endpoints additionally require
`BIDDING_ROUND_URL_ENABLED`.

```mermaid
flowchart TD
    A["Request: page or API"] --> B{"BIDDING_ROUND_ENABLED?"}
    B -- No --> E404["404 Not Found"]
    B -- Yes --> C{"Public, member-facing endpoint?"}
    C -- "No (admin page / admin API)" --> ADMIN["Handle request<br/>global IsAuthenticated + has_manage_permission"]
    C -- "Yes (public_data, public_results, capacity_check, member_bid)" --> D{"BIDDING_ROUND_URL_ENABLED?"}
    D -- No --> E404
    D -- Yes --> PUB["Handle request<br/>AllowAny / IsAuthenticated"]
```

### 2. Round lifecycle and status gates

```mermaid
stateDiagram-v2
    [*] --> CONFIGURATION: create_round
    CONFIGURATION --> ACTIVE: start_round
    ACTIVE --> CLOSED: close_round
    CLOSED --> ACTIVE: reopen_round
    CONFIGURATION --> [*]: delete_round
    CLOSED --> [*]: delete_round

    note right of CONFIGURATION
      start_round requires a target_amount_per_year
      and no other ACTIVE round.
    end note

    note left of CLOSED
      reopen_round and delete_round are blocked once
      contracts_created_at is set.
      lock_average_bid freezes the average bid
      (position 0-100, surcharge 0-100%);
      unlock_average_bid is blocked after contracts.
    end note
```

### 3. Member bidding flow (frontend steps, checks and backend gates)

```mermaid
flowchart TD
    START["Open /bidding_rounds/"] --> ENABLED{"Feature and URL enabled<br/>and a round is open?"}
    ENABLED -- No --> INTRO_END["Intro step: 'not available' / 'ended'"]
    ENABLED -- Yes --> AUTH{"Logged in?"}
    AUTH -- No --> LOGIN["Intro with login button<br/>login returns to /bidding_rounds/"]
    AUTH -- Yes --> SKIP_INTRO{"skip_intro=1?"}
    SKIP_INTRO -- No --> S_INTRO["bidding_round_intro step"]
    SKIP_INTRO -- Yes --> SKIP_DESC
    S_INTRO --> SKIP_DESC{"skip_product_description=1?"}
    SKIP_DESC -- No --> S_DESC["product description step"]
    SKIP_DESC -- Yes --> S_BID
    S_DESC --> S_BID["Bid step: amounts and quantity"]
    S_BID --> CHECK_CAP{"capacity_check sufficient?"}
    CHECK_CAP -- No --> S_BID
    CHECK_CAP -- Yes --> PICK_ENABLED{"Pickup change enabled?"}
    PICK_ENABLED -- Yes --> S_PICK["Pickup step:<br/>select depot, capacity_check on select and next"]
    PICK_ENABLED -- No --> S_SUM
    S_PICK --> S_SUM["Summary step:<br/>location and yearly delivery charge"]
    S_SUM --> SUBMIT["POST /member_bid"]
    SUBMIT --> VALID{"BidValidator:<br/>round open (status ACTIVE, start_at/end_at),<br/>items present, levels, min amount,<br/>ascending order, quantity flag,<br/>pickup exists, capacity"}
    VALID -- Invalid --> E400["400 with message, shown in the form"]
    VALID -- Valid --> SAVE["save_bid (atomic, select_for_update):<br/>upsert bid + items,<br/>mail bid received/updated"]
    SAVE --> CONFIRM["Confirmation step"]
```

### 4. Pickup-location decision

```mermaid
flowchart TD
    A["save_bid(member, pickup_location_id)"] --> B{"BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED?"}
    B -- Yes --> C["Keep submitted pickup_location_id<br/>validate it exists"]
    B -- No --> D["Ignore submitted value,<br/>use the member's current location"]
    C --> E["Validate capacity for that location"]
    D --> E
    E --> F["Persist bid"]
    F --> G["public_data / member_bid always expose<br/>current_pickup_location: id, name, yearly delivery charge"]
```

### 5. Evaluation, average-bid lock and contract creation/deletion

```mermaid
flowchart TD
    CLOSED["Round is CLOSED"] --> RESULTS["Results / evaluation<br/>BiddingRoundStatsService"]
    RESULTS --> LOCK{"lock_average_bid<br/>position + surcharge 0-100%"}
    LOCK -- "already locked / surcharge out of range" --> LOCK
    LOCK -- ok --> LOCKED["average_bid_locked_at set"]
    LOCKED --> CONFIRM{"All selected bids confirmed<br/>(admin_confirmed)?"}
    CONFIRM -- "unconfirmed" --> REJECT["create_contracts rejected,<br/>lists the unconfirmed members"]
    CONFIRM -- "all confirmed" --> CREATE["create_contracts_from_bids"]
    CREATE --> GATES{"Gates: status CLOSED,<br/>contracts_created_at is None,<br/>average bid locked?"}
    GATES -- No --> E400["400 ValidationError"]
    GATES -- Yes --> PER_BID["Per bid (transaction.atomic):<br/>snapshot replaced subscriptions<br/>then create new subscriptions"]
    PER_BID --> ERRORS{"Any bid failed?"}
    ERRORS -- Yes --> REPORT["Report errors per bid; if nothing was<br/>created, contracts_created_at stays unset (retryable)"]
    ERRORS -- No --> DONE["contracts_created_at set<br/>(only when >=1 subscription created)"]
    DONE --> DELETE{"delete_contracts"}
    DELETE -- "contracts_created_at is None" --> DERR["400 ValidationError"]
    DELETE -- ok --> RESTORE["Delete round subscriptions,<br/>restore BiddingRoundReplacedSubscription snapshots,<br/>revert non-bidder contributions"]
```

### Checks and gates summary

| Gate | Rule | Where |
|---|---|---|
| Master flag | `BIDDING_ROUND_ENABLED=false` -> 404 everywhere | `permissions.py` |
| Public URL flag | `BIDDING_ROUND_URL_ENABLED=false` -> 404 for public/member endpoints only | `permissions.py` |
| Round start | needs `target_amount_per_year`, no other ACTIVE round | `BiddingRoundService.start_round` |
| Round reopen/delete | blocked once `contracts_created_at` is set | `BiddingRoundService.reopen_round` / `delete_round` |
| Member bid | only Members; round `ACTIVE`, `start_at <= now <= end_at`; atomic + row lock | `save_bid`, `BidValidator._validate_round_is_open` |
| Item | shares belong to the round, product to the product type, amounts finite/non-negative/ascending, min amount, quantity 1-5 | `BidValidator._validate_item` / `_validate_levels` / `_parse_amounts` |
| Quantity flag | `BIDDING_ROUND_BID_QUANTITY_ENABLED=false` -> only `quantity == 1` | `BidValidator._is_quantity_enabled` |
| Pickup | when change is off, submitted location is ignored; otherwise must exist | `BiddingRoundService._resolve_pickup_location_id`, `BidValidator._validate_pickup_locations` |
| Capacity | products/quantity/location must fit remaining capacity | `BidValidator._validate_capacity`, `capacity_check` |
| Bid edit after contracts | item changes and pickup changes are blocked | `save_admin_bid` |
| Lock average bid | not already locked; surcharge 0-100% | `BiddingRoundService.lock_average_bid` |
| Unlock average bid | blocked once `contracts_created_at` is set | `BiddingRoundService.unlock_average_bid` |
| Create contracts | `CLOSED`, average bid locked, not already created, all selected bids confirmed | `ContractCreator.create_contracts_from_bids` |
| Delete contracts | requires `contracts_created_at` set | `BiddingRoundContractDeletionService.delete_contracts` |

## Tests

`make test-app APP=bidding_round`. The end-to-end demo data comes from
`tapir/utils/services/test_data_generation/bidding_round_generator.py`.
