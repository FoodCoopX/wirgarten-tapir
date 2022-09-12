from django.apps import AppConfig


class WirgartenConfig(AppConfig):
    name = "tapir.wirgarten"

    def ready(self):
        from tapir.wirgarten.parameters import load_params

        load_params()
