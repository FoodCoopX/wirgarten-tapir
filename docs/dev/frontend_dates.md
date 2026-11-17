# Dates in the frontend

The API has two kinds of date fields, and the frontend handles them differently.

| API field              | OpenAPI format | Example                       | Type in the generated client |
|------------------------|----------------|-------------------------------|------------------------------|
| Django `DateField`     | `date`         | `"2026-06-01"`                | `string`                     |
| Django `DateTimeField` | `date-time`    | `"2026-06-01T14:30:00+02:00"` | `Date`                       |

A date-only field is a calendar date: it has no time and no time zone. The generated client
keeps it as a `"YYYY-MM-DD"` string, because `scripts/generate_api_clients.sh` runs the
generator with `--type-mappings=date=string`.

## Why not `Date`?

A JavaScript `Date` is a moment in time, not a calendar date. Before date-only fields were
strings, the generated client converted them in both directions:

- **Reading:** `new Date("2026-06-01")` parses a date-only string as midnight **UTC**. Reading
  it with local getters (`getDate()`, `getDay()`, …) can give the previous day, depending on
  the browser's time zone.
- **Sending:** `toISOString().substring(0, 10)` converts to UTC first. A date picked at local
  midnight in Germany was sent as the previous day.

The frontend worked around this with `Date.UTC(...)` and `getUTC…()` in several places. Every
new date field needed the same workaround, and forgetting it caused off-by-one-day bugs.

## Rules

- **Never** call `new Date(value)` on a date-only string. It parses the string as UTC.
- Convert with the helpers in `src_frontend/utils/apiDate.ts`, which work in local time:
    - `fromApiDate("2026-06-01")` gives local midnight of that day as a `Date`.
    - `toApiDate(date)` gives the local calendar day of a `Date` as `"YYYY-MM-DD"`.
- A value from `<input type="date">` is already `"YYYY-MM-DD"`: send it as it is.
- Compare and sort date-only strings as strings. For `"YYYY-MM-DD"`, string order is date
  order: `a < b`, `a.localeCompare(b)`.
- To compare with today, use `toApiDate(new Date())`. This is the browser's local day, which
  can differ from the server's day (`Europe/Berlin`) for a few hours around midnight for users
  in other time zones.
- Pass date-only values to the `formatDate…` helpers in `src_frontend/utils/` as strings: a
  string is always formatted as the calendar date it represents. Never pass `fromApiDate(...)`,
  or a `Date` derived from it, to `formatDateNumeric`: it formats `Date`s in `Europe/Berlin`
  (for date-times), so local midnight shows as the previous day for users east of Berlin. If you
  only have a `Date`, format `toApiDate(date)`. The other formatters use the browser's time zone.

## Examples

```tsx
// Display
formatDateNumeric(payment.dueDate);

// Is the period in the future?
period.startDate > toApiDate(new Date());

// Sort by due date
payments.toSorted((a, b) => a.dueDate.localeCompare(b.dueDate));

// Send a Date held in state
api.someCreate({ request: { validFrom: toApiDate(validFrom) } });

// Need date arithmetic? Convert to Date first
dayjs(fromApiDate(subscription.startDate)).add(1, "month");
```
