from django.core import mail
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from tapir.utils.services.celery_task_failure_mail_sender import (
    CeleryTaskFailureMailSender,
)


@override_settings(
    ADMINS=["errors@example.com"],
    SITE_URL="https://tapir.test",
    # we use a memory cache instead of redis so that the tests don't use a shared redis cache
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class TestCeleryTaskFailureMailSender(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    @staticmethod
    def _fail(task_name: str = "tapir.test_task", exception: Exception = None):
        CeleryTaskFailureMailSender.on_task_failure(
            task_name=task_name,
            task_id="task-id",
            exception=exception or ValueError("broken"),
            traceback="the traceback",
        )

    def test_onTaskFailure_firstFailure_sendsMail(self):
        self._fail()

        self.assertEqual(1, len(mail.outbox))
        self.assertIn("tapir.test_task", mail.outbox[0].subject)
        self.assertIn("https://tapir.test", mail.outbox[0].subject)
        self.assertIn("ValueError('broken')", mail.outbox[0].body)
        self.assertIn("the traceback", mail.outbox[0].body)
        self.assertNotIn("more time(s)", mail.outbox[0].body)

    def test_onTaskFailure_repeatedFailureWithinThrottle_sendsNoMail(self):
        self._fail()
        self._fail()
        self._fail()

        self.assertEqual(1, len(mail.outbox))

    def test_onTaskFailure_otherTaskOrExceptionType_sendsMail(self):
        self._fail()
        self._fail(task_name="tapir.other_task")
        self._fail(exception=KeyError("broken"))

        self.assertEqual(3, len(mail.outbox))

    def test_onTaskFailure_throttleExpired_sendsMailWithSuppressedCount(self):
        self._fail()
        self._fail()
        self._fail()
        cache.delete(
            CeleryTaskFailureMailSender._build_throttle_key(
                task_name="tapir.test_task", exception=ValueError()
            )
        )

        self._fail()

        self.assertEqual(2, len(mail.outbox))
        self.assertIn("2 more time(s)", mail.outbox[1].body)

    def test_onTaskFailure_afterMailWithSuppressedCount_counterIsReset(self):
        throttle_key = CeleryTaskFailureMailSender._build_throttle_key(
            task_name="tapir.test_task", exception=ValueError()
        )
        self._fail()
        self._fail()
        cache.delete(throttle_key)
        self._fail()
        cache.delete(throttle_key)

        self._fail()

        self.assertEqual(3, len(mail.outbox))
        self.assertNotIn("more time(s)", mail.outbox[2].body)
