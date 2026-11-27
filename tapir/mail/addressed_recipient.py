from dataclasses import dataclass, field

from tapir.mail.models import StaticSegmentRecipient
from tapir.mail.triggers.transactional_trigger import TransactionalTriggerData
from tapir.wirgarten.models import Member

type MailRecipient = (
    Member
    | StaticSegmentRecipient
    | TransactionalTriggerData.RecipientOutsideOfBaseQueryset
)


@dataclass
class AddressedRecipient:
    recipient: MailRecipient
    email: str
    token_overrides: dict = field(default_factory=dict)

    @classmethod
    def at_own_address(cls, recipient: MailRecipient) -> "AddressedRecipient":
        return cls(recipient=recipient, email=recipient.email)

    @property
    def is_extra_address(self) -> bool:
        return self.email != self.recipient.email
