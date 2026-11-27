import datetime

from django.core import signing


class SubscriptionManagementTokenSigner:
    SALT = "tapir.core.subscription_management"
    VALIDITY_HOURS = 72

    @classmethod
    def sign(cls, address: str) -> str:
        return signing.dumps(address, salt=cls.SALT)

    @classmethod
    def get_address(cls, token: str) -> str | None:
        try:
            return signing.loads(
                token,
                salt=cls.SALT,
                max_age=datetime.timedelta(hours=cls.VALIDITY_HOURS),
            )
        except signing.BadSignature:
            return None
