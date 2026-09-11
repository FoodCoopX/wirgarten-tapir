from celery import shared_task

from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)


@shared_task
def do_automated_exports():
    cache = {}
    AutomatedExportsManager.do_automated_csv_exports(cache=cache)
    AutomatedExportsManager.do_automated_pdf_exports(cache=cache)
