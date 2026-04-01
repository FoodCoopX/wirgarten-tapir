from enum import Enum


class Organization(Enum):
    WIRGARTEN = "wirgarten"
    BIOTOP = "biotop"
    VEREIN = "verein"
    L2G = "l2g"
    MM = "mm"


MEMBER_IMPORT_STATUS_SKIPPED = "member_skipped"
MEMBER_IMPORT_STATUS_UPDATED = "member_updated"
MEMBER_IMPORT_STATUS_CREATED = "member_created"
