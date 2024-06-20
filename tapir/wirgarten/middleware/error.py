import os
import traceback

from django.conf import settings

from tapir.wirgarten.utils import get_now


class GlobalServerErrorHandlerMiddleware:
    """
    This middleware catches all unhandled exceptions and saves the stacktrace to the 'settings.ERROR_LOG_DIR' file.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        timestamp = get_now().strftime("%Y-%m-%d_%H-%M-%S")
        error_log_dir = (
            settings.ERROR_LOG_DIR
            if hasattr(settings, "ERROR_LOG_DIR")
            else "error_logs"
        )
        error_log_filename = f"{error_log_dir}/error_log_{timestamp}.txt"

        if not settings.DEBUG:
            traceback.print_exc()

        try:
            if not os.path.exists(error_log_dir):
                os.makedirs(error_log_dir)

            with open(error_log_filename, "w") as error_log_file:
                error_log_file.write(f"Error while calling URL: {request.path}\n")
                traceback.print_exc(file=error_log_file)

            print(
                f"\n\033[93m>>>>> saved stacktrace in:  {error_log_filename}\n\033[0m"
            )
        except Exception as e:
            print("Error while dumping error log: ", e)
            print("Original Exception: ", exception)
