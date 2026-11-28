from tapir.mail.models import EmailDispatch
from tapir.mail.tests.factories import EmailDispatchFactory


class TestUtils:
    @staticmethod
    def create_email_dispatches(
        count,
        config_dispatch,
        error_message=None,
        sent_time=None,
        created_at=None,
        recipient_prefix="test",
    ) -> list[EmailDispatch]:
        dispatches = EmailDispatch.objects.bulk_create(
            EmailDispatchFactory.build(
                email_configuration_dispatch=config_dispatch,
                error_message=error_message,
                recipient=f"{recipient_prefix}{i}@example.com",
                sent_time=sent_time,
            )
            for i in range(count)
        )

        if created_at is not None:
            EmailDispatch.objects.filter(id__in=[d.id for d in dispatches]).update(
                created_at=created_at
            )

        return dispatches
