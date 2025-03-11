from celery import shared_task

from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)


@shared_task
def do_automated_exports():
    AutomatedExportsManager.do_automated_exports()
