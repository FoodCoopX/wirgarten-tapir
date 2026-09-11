from enum import Enum


class Organization(Enum):
    WIRGARTEN = "wirgarten"
    BIOTOP = "biotop"
    VEREIN = "verein"
    L2G = "l2g"
    MM = "mm"
    # Not an installation of its own: the BIOTOP setup plus the bakery, so
    # that `populate --org=bakery` gives a local instance with breads,
    # capacities and member preferences ready to reproduce bug reports on.
    BAKERY = "bakery"


# Every per-organization setting is keyed on a real installation, so BAKERY is
# resolved to the one it layers on before any of them is read.
BAKERY_BASE_ORGANIZATION = Organization.BIOTOP


MEMBER_IMPORT_STATUS_SKIPPED = "member_skipped"
MEMBER_IMPORT_STATUS_UPDATED = "member_updated"
MEMBER_IMPORT_STATUS_CREATED = "member_created"
