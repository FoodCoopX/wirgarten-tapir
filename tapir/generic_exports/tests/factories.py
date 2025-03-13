import factory
from faker import Faker

from tapir.generic_exports.models import CsvExport, AutomatedExportCycle, PdfExport
from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager
from tapir.wirgarten.models import ExportedFile

fake = Faker()
Faker.seed("tapir")


class CsvExportFactory(factory.django.DjangoModelFactory[CsvExport]):
    class Meta:
        model = CsvExport

    export_segment_id = factory.Faker(
        "random_element",
        elements=ExportSegmentManager.registered_export_segments.keys(),
    )
    name = factory.Faker("bs")
    description = factory.Faker("bs")
    separator = factory.Faker("random_element", elements=[",", ";", "-"])
    automated_export_cycle = factory.Faker(
        "random_element",
        elements=[x[0] for x in AutomatedExportCycle.choices],
    )
    automated_export_day = factory.Faker("pyint", min_value=1, max_value=365)
    automated_export_hour = factory.Faker("time")

    @factory.post_generation
    def email_recipients(self: CsvExport, create, email_recipients, **kwargs):
        if not create:
            return

        if not email_recipients:
            nb_recipients = fake.pyint(min_value=1, max_value=5)
            email_recipients = [fake.email() for _ in range(nb_recipients)]

        self.email_recipients = email_recipients

    @factory.post_generation
    def column_ids(self: CsvExport, create, column_ids, **kwargs):
        if not create:
            return

        if not column_ids:
            possible_ids = [
                column.id
                for column in ExportSegmentManager.registered_export_segments[
                    self.export_segment_id
                ].get_available_columns()
            ]
            column_ids = fake.random_elements(possible_ids, unique=True)

        self.column_ids = column_ids

    @factory.post_generation
    def custom_column_names(self: CsvExport, create, names, **kwargs):
        if not create:
            return

        if not names:
            names = [fake.bs() for _ in self.column_ids]

        self.custom_column_names = names


class PdfExportFactory(factory.django.DjangoModelFactory[PdfExport]):
    class Meta:
        model = PdfExport

    export_segment_id = factory.Faker(
        "random_element",
        elements=ExportSegmentManager.registered_export_segments.keys(),
    )
    name = factory.Faker("bs")
    description = factory.Faker("bs")
    automated_export_cycle = factory.Faker(
        "random_element",
        elements=[x[0] for x in AutomatedExportCycle.choices],
    )
    automated_export_day = factory.Faker("pyint", min_value=1, max_value=365)
    automated_export_hour = factory.Faker("time")
    template = factory.Faker("bs")
    generate_one_file_for_every_segment_entry = factory.Faker("pybool")

    @factory.post_generation
    def email_recipients(self: CsvExport, create, email_recipients, **kwargs):
        if not create:
            return

        if not email_recipients:
            nb_recipients = fake.pyint(min_value=1, max_value=5)
            email_recipients = [fake.email() for _ in range(nb_recipients)]

        self.email_recipients = email_recipients


class ExportedFileFactory(factory.django.DjangoModelFactory[ExportedFile]):
    class Meta:
        model = ExportedFile

    name = factory.Faker("bs")
    type = factory.Faker(
        "random_element",
        elements=[x[0] for x in ExportedFile.FileType.choices],
    )
    file = factory.Faker("binary")
