import random
from tapir.wirgarten.parameters import ParameterDefinitions
import datetime
from pathlib import Path

from tapir.generic_exports.models import PdfExport
from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.pickup_locations.services.pickup_location_segment_provider import (
    PickupLocationSegmentProvider,
)
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    ProductPriceFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.constants import WEEKLY


class TestLocationRoutePdfExport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_createExportedFiles_typst(self):
        now = datetime.datetime(year=2020, month=7, day=17)

        # Fill the database
        pickup_locations = [PickupLocationFactory.create() for _ in range(3)]
        products = [
            ProductFactory.create(type__delivery_cycle=WEEKLY[0]) for _ in range(2)
        ]
        for product in products:
            ProductPriceFactory.create(
                product=product,
                valid_from=now - datetime.timedelta(days=100),
            )
        for _ in range(5):
            member = MemberFactory.create()
            MemberPickupLocationFactory.create(
                member=member,
                pickup_location=random.choice(pickup_locations),
                valid_from=now - datetime.timedelta(days=30),
            )
            SubscriptionFactory.create(
                member=member,
                start_date=now - datetime.timedelta(days=30),
                end_date=now + datetime.timedelta(days=30),
                product=random.choice(products),
            )

        pdf_export = PdfExport(
            file_name="location_routes.pdf",
            export_segment_id=PickupLocationSegmentProvider.SEGMENT_ID_ALL_LOCATION_ROUTES,
            template=Path(
                "tapir/pickup_locations/templates/location_routes_template.typ"
            ).read_text(encoding="utf-8"),
        )

        # Perform the PDF rendering
        [result] = PdfExportBuilder.create_exported_files(
            pdf_export,
            now,
        )

        # Inspect the exported file
        # Path("test_location_route_pdf_export.pdf").write_bytes(result.file)
        self.assertEqual("location_routes.2020.07.17 00.00.pdf", result.name)
        self.assertEqual("pdf", result.type)
        self.assertTrue(10_000 <= len(result.file) <= 1_000_000, len(result.file))
