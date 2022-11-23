from django.utils.translation import gettext_lazy as _

DeliveryCycle = [
    NO_DELIVERY := ("no_delivery", _("Keine Lieferung/Abholung")),
    WEEKLY := ("weekly", _("1x pro Woche")),
    ODD_WEEKS := ("odd_weeks", _("2x pro Monat (ungerade KW)")),
    EVEN_WEEKS := ("even_weeks", _("2x pro Monat (gerade KW)")),
    MONTHLY := ("monthly", _("1x pro Monat")),
]


class ProductTypes:
    HARVEST_SHARES = "Ernteanteile"
    CHICKEN_SHARES = "Hühneranteile"
    BESTELLCOOP = "BestellCoop"
