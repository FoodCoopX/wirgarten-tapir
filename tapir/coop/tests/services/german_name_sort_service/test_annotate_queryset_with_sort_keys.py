from tapir.coop.services.german_name_sort_service import GermanNameSortService
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAnnotateQuerysetWithSortKeys(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_annotateQuerysetWithSortKeys_lastNameWithUmlaut_sortsAsIfUmlautWereSpelledOut(
        self,
    ):
        haeuser = MemberFactory.create(first_name="Anna", last_name="Häuser")
        heyne = MemberFactory.create(first_name="Bert", last_name="Heyne")

        queryset = GermanNameSortService.annotate_queryset_with_sort_keys(
            Member.objects.all(), ["last_name"], cache={}
        ).order_by("last_name_sort_key")

        self.assertEqual(
            [haeuser.id, heyne.id], list(queryset.values_list("id", flat=True))
        )

    def test_annotateQuerysetWithSortKeys_namesWithDifferentUmlauts_sortsCaseInsensitivelyAndByReplacedSpelling(
        self,
    ):
        oertel = MemberFactory.create(first_name="Anna", last_name="Ötztal")
        ostermann = MemberFactory.create(first_name="Bert", last_name="Ostermann")
        ueberacker = MemberFactory.create(first_name="Carla", last_name="Überacker")

        queryset = GermanNameSortService.annotate_queryset_with_sort_keys(
            Member.objects.all(), ["last_name"], cache={}
        ).order_by("last_name_sort_key")

        self.assertEqual(
            [oertel.id, ostermann.id, ueberacker.id],
            list(queryset.values_list("id", flat=True)),
        )

    def test_annotateQuerysetWithSortKeys_multipleFieldNames_annotatesEachWithItsOwnSortKey(
        self,
    ):
        member = MemberFactory.create(first_name="Ännchen", last_name="Müller")

        queryset = GermanNameSortService.annotate_queryset_with_sort_keys(
            Member.objects.all(), ["first_name", "last_name"], cache={}
        )

        annotated_member = queryset.get(id=member.id)
        self.assertEqual("aennchen", annotated_member.first_name_sort_key)
        self.assertEqual("mueller", annotated_member.last_name_sort_key)
