import inspect

from django.utils.translation import gettext_lazy as _

DeliveryCycle = [
    NO_DELIVERY := ("no_delivery", _("Keine Lieferung/Abholung")),
    WEEKLY := ("weekly", _("1x pro Woche")),
    ODD_WEEKS := ("odd_weeks", _("Jede 2. Woche (ungerade KW)")),
    EVEN_WEEKS := ("even_weeks", _("Jede 2. Woche (gerade KW)")),
    EVERY_FOUR_WEEKS := (
        "every_four_weeks",
        _("Jede 4. Woche"),
    ),
    CUSTOM_CYCLE := (
        "custom",
        _("Benutzerdefinierte Lieferwochen"),
    ),
]

DeliveryCycleDict = dict(DeliveryCycle)

OPTIONS_WEEKDAYS = [
    (0, _("Montag")),
    (1, _("Dienstag")),
    (2, _("Mittwoch")),
    (3, _("Donnerstag")),
    (4, _("Freitag")),
    (5, _("Samstag")),
    (6, _("Sonntag")),
]


class ParameterCategory:
    BESTELLWIZARD = "BestellWizard"
    BUSINESS = "{{legal_status}}"
    DELIVERY = "Lieferung"
    JOKERS = "Joker"
    MAIL = "E-Mails"
    MEMBER_DASHBOARD = "Mitgliederbereich"
    ORGANIZATION = "Organisation"
    PAYMENT = "Zahlungen"
    PICKING = "Kommissionierung"
    SITE = "Standort"
    SOLIDARITY = "Solidarbeitrag"
    SUBSCRIPTIONS = "Verträge"
    SUPPLIER_LIST = "Lieferantenliste"
    TEST = "Tests"
    TRIAL_PERIOD = "Probezeit"


HTML_ALLOWED_TEXT = "HTML erlaubt"


class Permission:
    permission_strings = False

    @staticmethod
    def all() -> list[str]:
        if not Permission.permission_strings:
            perms = []
            internal_classes = [
                member[1]
                for member in inspect.getmembers(Permission)
                if inspect.isclass(member[1])
            ]
            for clazz in internal_classes:
                for field in filter(lambda x: not x.startswith("_"), dir(clazz)):
                    perm = getattr(clazz, field)
                    if type(perm) is str:
                        perms.append(perm)

            Permission.permission_strings = perms
        return Permission.permission_strings

    class Coop:
        VIEW = "coop.view"
        MANAGE = "coop.manage"

    class Accounts:
        VIEW = "accounts.view"
        MANAGE = "accounts.manage"

    class Payments:
        VIEW = "payments.view"
        MANAGE = "payments.manage"

    class Products:
        VIEW = "products.view"
        MANAGE = "products.manage"

    class Email:
        MANAGE = "email.manage"
