from io import StringIO

from django.contrib.auth.models import Permission as PermissionModel
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import GrowingPeriod
from tapir.wirgarten.models import Product


class KeycloakTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.now = now = timezone.now()

        fixtures = [
            "0010_pickup_locations",
            "0020_product_types",
            "0021_tax_rates",
            "0030_products",
            "0031_product_prices",
            "0040_growing_periods",
            "0050_product_capacity",
            "0060_pickup_location_capabilities",
        ]
        for fix in fixtures:
            call_command(
                "loaddata",
                f"tapir/wirgarten/fixtures/{fix}",
                app="wirgarten",
                stdout=StringIO(),
            )

        call_command("parameter_definitions", stdout=StringIO())

        permissions = [
            (Permission.Products.VIEW, ContentType.objects.get_for_model(Product)),
        ]
        for codename, ct in permissions:
            PermissionModel.objects.get_or_create(
                content_type=ct,
                codename=codename,
            )

        GrowingPeriod.objects.create(
            start_date=now.replace(year=now.year - 1, month=3, day=1),
            end_date=now.replace(year=now.year + 1, month=2, day=28),
        )


class KeycloakServiceTestCase(KeycloakTestCase):
    """base class to interact with a running Keycloak service"""

    pass
