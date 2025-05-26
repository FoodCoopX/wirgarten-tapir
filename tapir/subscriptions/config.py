NOTICE_PERIOD_UNIT_MONTHS = "months"
NOTICE_PERIOD_UNIT_WEEKS = "weeks"

NOTICE_PERIOD_UNIT_OPTIONS = [
    (NOTICE_PERIOD_UNIT_MONTHS, "Monate"),
    (NOTICE_PERIOD_UNIT_WEEKS, "Wochen"),
]


SOLIDARITY_UNIT_PERCENT = "percentage"
SOLIDARITY_UNIT_ABSOLUTE = "absolute"

SOLIDARITY_UNIT_OPTIONS = [
    (SOLIDARITY_UNIT_PERCENT, "Prozent"),
    (SOLIDARITY_UNIT_ABSOLUTE, "Absolut"),
]

SOLIDARITY_MODE_ONLY_POSITIVE = 0
SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED = 1
SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE = 2
SOLIDARITY_MODE_OPTIONS = [
    (
        SOLIDARITY_MODE_ONLY_POSITIVE,
        "Nur positive Solidarpreise möglich (Mitglieder können keinen niedrigeren Preis wählen)",
    ),
    (
        SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
        "Negative Solidarpreise möglich (Mitglieder können immer einen niedrigeren Preis wählen)",
    ),
    (
        SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
        "Automatische Berechnung (niedrigere Preise sind möglich, wenn genügend Mitglieder mehr zahlen)",
    ),
]
