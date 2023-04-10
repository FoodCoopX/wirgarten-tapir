import os
import sys
import traceback
from datetime import datetime

from django.http import HttpResponseServerError
from django.views import debug

from tapir import settings


class GlobalServerErrorHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            self.handle_server_error(request, e)
            if settings.DEBUG:
                return debug.technical_500_response(request, *sys.exc_info())
            else:
                return HttpResponseServerError("Internal Server Error")

    def handle_server_error(self, request, exception):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        error_log_dir = (
            settings.ERROR_LOG_DIR
            if "ERROR_LOG_DIR" in settings.__dict__
            else "error_logs"
        )
        error_log_filename = f"{error_log_dir}/error_log_{timestamp}.txt"

        traceback.print_exc()

        try:
            if not os.path.exists(error_log_dir):
                os.makedirs(error_log_dir)

            with open(error_log_filename, "w") as error_log_file:
                traceback.print_exc(file=error_log_file)

            print(
                f"\n\033[93m>>>>> saved stacktrace in:  {error_log_filename}\n\033[0m"
            )
        except Exception as e:
            print("Error while dumping error log: ", e)
            print("Original Exception: ", exception)
