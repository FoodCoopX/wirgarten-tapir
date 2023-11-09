import inspect

from django.utils.translation import gettext_lazy as _

DeliveryCycle = [
    NO_DELIVERY := ("no_delivery", _("Keine Lieferung/Abholung")),
    WEEKLY := ("weekly", _("1x pro Woche")),
    ODD_WEEKS := ("odd_weeks", _("2x pro Monat (ungerade KW)")),
    EVEN_WEEKS := ("even_weeks", _("2x pro Monat (gerade KW)")),
    #    MONTHLY := ("monthly", _("1x pro Monat")),
]

DeliveryCycleDict = {key: value for key, value in DeliveryCycle}

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
        # ADMIN = "coop.admin"

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
