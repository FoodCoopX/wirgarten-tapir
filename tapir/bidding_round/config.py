"""Constants for the bidding round.

The status describes the lifecycle of a round: configuration → active → closed.
The values are database content and stay unchanged; only the Python names were
given more precise domain names. The shares per bid are limited to
BIDDING_ROUND_MIN_SHARES through BIDDING_ROUND_MAX_SHARES.
"""

from django.utils.translation import gettext_lazy as _

BIDDING_ROUND_STATUS_CONFIGURATION = "configuration"
BIDDING_ROUND_STATUS_ACTIVE = "active"
BIDDING_ROUND_STATUS_CLOSED = "closed"
BIDDING_ROUND_MIN_SHARES = 1
BIDDING_ROUND_MAX_SHARES = 5

OPTIONS_BIDDING_ROUND_STATUS = [
    (BIDDING_ROUND_STATUS_CONFIGURATION, _("Konfiguration")),
    (BIDDING_ROUND_STATUS_ACTIVE, _("Aktiv")),
    (BIDDING_ROUND_STATUS_CLOSED, _("Abgeschlossen")),
]
