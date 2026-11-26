from typing import Callable

from django.db import models


class TransactionalTriggerKeys:
    MAIL_CATEGORY_REGISTRATION_CONFIRMATION_LINK = (
        "mail_category_registration_confirmation_link"
    )
    MAIL_CATEGORY_REGISTRATION_CONFIRMED = "mail_category_registration_confirmed"


type BccProvider = Callable[[], str]


class ExternalConfig:
    USER_MODEL: models.Model | None = None
    MASS_MAIL_BCC_PROVIDER: BccProvider | None = None
    TRANSACTIONAL_MAIL_BCC_PROVIDER: BccProvider | None = None
