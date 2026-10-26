from django.utils.translation import gettext_lazy as _

CONFIGURATION = "configuration"
ACTIVE = "active"
CLOSED = "closed"

SIMPLE = "simple"
TRAFFIC_LIGHT = "traffic_light"

SOLIDARITY = "solidarity"

OPTIONS_BIDDING_ROUND_STATUS = [
    (CONFIGURATION, _("Configuration")),
    (ACTIVE, _("Active")),
    (CLOSED, _("Closed")),
]

OPTIONS_BIDDING_ROUND_PROCEDURE = [
    (SIMPLE, _("Simple")),
    (TRAFFIC_LIGHT, _("Traffic light")),
]
