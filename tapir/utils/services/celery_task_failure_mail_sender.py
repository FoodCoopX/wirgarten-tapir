from django.conf import settings
from django.core.cache import cache
from django.core.mail import mail_admins


class CeleryTaskFailureMailSender:
    THROTTLE_SECONDS = 60 * 60

    @classmethod
    def on_task_failure(
        cls, task_name: str, task_id: str, exception: BaseException, traceback: str
    ):
        throttle_key = cls._build_throttle_key(task_name=task_name, exception=exception)
        suppressed_count_key = f"{throttle_key}:suppressed"

        if not cache.add(throttle_key, True, timeout=cls.THROTTLE_SECONDS):
            if not cache.add(suppressed_count_key, 1, timeout=None):
                cache.incr(suppressed_count_key)
            return

        suppressed_count = cache.get(suppressed_count_key, 0)
        cache.delete(suppressed_count_key)

        mail_admins(
            subject=f"[celery@{settings.SITE_URL}] Error: Task {task_name} ({task_id})",
            message=cls._build_message(
                task_name=task_name,
                task_id=task_id,
                exception=exception,
                traceback=traceback,
                suppressed_count=suppressed_count,
            ),
        )

    @staticmethod
    def _build_throttle_key(task_name: str, exception: BaseException) -> str:
        return f"celery_task_failure_mail:{task_name}:{type(exception).__name__}"

    @classmethod
    def _build_message(
        cls,
        task_name: str,
        task_id: str,
        exception: BaseException,
        traceback: str,
        suppressed_count: int,
    ) -> str:
        message = (
            f"Task {task_name} with id {task_id} raised exception: {exception!r}\n\n"
        )
        if suppressed_count:
            message += (
                f"This task failed with the same exception type {suppressed_count} more time(s) "
                f"since the last mail. Further failures are reported at most once every "
                f"{cls.THROTTLE_SECONDS // 60} minutes.\n\n"
            )
        message += f"Traceback:\n{traceback}"
        return message
