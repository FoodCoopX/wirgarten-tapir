from django.utils.translation import gettext_lazy as _

CONFIGURATION = "configuration"
ACTIVE = "active"
CLOSED = "closed"

SIMPLE = "simple"
TRAFFIC_LIGHT = "traffic_light"

SOLIDARITY = "solidarity"

OPTIONS_BIDDING_ROUND_STATUS = [
    (CONFIGURATION, _("Konfiguration")),
    (ACTIVE, _("Aktiv")),
    (CLOSED, _("Abgeschlossen")),
]

OPTIONS_BIDDING_ROUND_PROCEDURE = [
    (SIMPLE, _("Einfach")),
    (TRAFFIC_LIGHT, _("Ampel")),
]
