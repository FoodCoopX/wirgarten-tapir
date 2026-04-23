import datetime
import random

from django.utils import timezone

from tapir.payments.models import MemberCredit
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today


class MemberCreditGenerator:
    @classmethod
    def generate_member_credits(cls):
        random.seed("wirgarten")
        members = list(Member.objects.filter(email__endswith="@example.com"))
        if not members:
            print("No members found, skipping credit generation")
            return

        credits_to_create = []
        today = get_today({})

        for member in members:
            if random.random() < 0.1:
                num_credits = random.randint(1, 3)
                for _ in range(num_credits):
                    due_date = today + datetime.timedelta(days=random.randint(1, 90))
                    amount = random.choice([25, 50, 75, 100, 150])
                    purpose = random.choice(
                        [
                            "Guthaben aus Überzahlung",
                            "Rückerstattung",
                            "Gutschrift für Wartezeit",
                            "Bonus",
                        ]
                    )
                    comment = f"Test-Gutschrift {random.randint(1000, 9999)}"
                    settled_on = (
                        timezone.make_aware(
                            datetime.datetime.combine(today, datetime.time(0, 0))
                            + datetime.timedelta(days=random.randint(1, 30))
                        )
                        if random.random() < 0.25
                        else None
                    )
                    credits_to_create.append(
                        MemberCredit(
                            due_date=due_date,
                            member=member,
                            amount=amount,
                            purpose=purpose,
                            comment=comment,
                            settled_on=settled_on,
                        )
                    )

        MemberCredit.objects.bulk_create(credits_to_create)
        print(f"Created {len(credits_to_create)} member credits")
