"""Constants for the bidding round.

The procedure describes the bid form: simple (1–3 levels) or bid_range
(exactly 2 levels: green/wish, red/pain threshold). The shares per bid are
limited to BIDDING_ROUND_MIN_SHARES through BIDDING_ROUND_MAX_SHARES.
"""

from django.utils.translation import gettext_lazy as _

BIDDING_ROUND_STATUS_CONFIGURATION = "configuration"
BIDDING_ROUND_STATUS_ACTIVE = "active"
BIDDING_ROUND_STATUS_CLOSED = "closed"
BIDDING_ROUND_MIN_SHARES = 1
BIDDING_ROUND_MAX_SHARES = 5

BIDDING_ROUND_PROCEDURE_SIMPLE = "simple"
BIDDING_ROUND_PROCEDURE_BID_RANGE = "bid_range"

OPTIONS_BIDDING_ROUND_STATUS = [
    (BIDDING_ROUND_STATUS_CONFIGURATION, _("Konfiguration")),
    (BIDDING_ROUND_STATUS_ACTIVE, _("Aktiv")),
    (BIDDING_ROUND_STATUS_CLOSED, _("Abgeschlossen")),
]

OPTIONS_BIDDING_ROUND_PROCEDURE = [
    (BIDDING_ROUND_PROCEDURE_SIMPLE, _("Einfaches Verfahren")),
    (BIDDING_ROUND_PROCEDURE_BID_RANGE, _("Gebotsspanne")),
]
