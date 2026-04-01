from django.conf import settings


def is_debug_instance():
    return getattr(settings, "DEBUG", False)
