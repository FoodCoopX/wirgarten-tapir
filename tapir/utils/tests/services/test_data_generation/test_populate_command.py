from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError

from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(DataGenerator, "generate_all")
@patch.object(DataGenerator, "clear")
class TestPopulateCommand(TapirIntegrationTest):
    def test_resetAll_noOrganization_defaultsToBiotop(self, _clear, mock_generate_all):
        # The READMEs use the no-argument form.
        call_command("populate", "--reset_all")

        self.assertEqual(mock_generate_all.call_args.args[0], Organization.BIOTOP)

    def test_resetAll_positionalOrganization_isUsed(self, _clear, mock_generate_all):
        call_command("populate", "--reset_all", "WIRGARTEN")

        self.assertEqual(mock_generate_all.call_args.args[0], Organization.WIRGARTEN)

    def test_resetAll_orgOptionIsCaseInsensitive(self, _clear, mock_generate_all):
        # Organization[...] is a name lookup, so the lowercase form has to be
        # upper-cased before it reaches the enum.
        call_command("populate", "--reset_all", "--org", "wirgarten")

        self.assertEqual(mock_generate_all.call_args.args[0], Organization.WIRGARTEN)

    def test_resetAll_unknownOrganization_raisesCommandErrorListingTheValidOnes(
        self, _clear, _generate_all
    ):
        with self.assertRaises(CommandError) as context:
            call_command("populate", "--reset_all", "--org", "nope")

        self.assertIn("BIOTOP", str(context.exception))

    def test_resetAll_withoutBakeryOrg_doesNotGenerateBakeryData(
        self, _clear, mock_generate_all
    ):
        call_command("populate", "--reset_all")

        self.assertNotEqual(mock_generate_all.call_args.args[0], Organization.BAKERY)

    def test_resetAll_orgBakery_generatesBakeryData(self, _clear, mock_generate_all):
        call_command("populate", "--reset_all", "--org", "bakery")

        self.assertEqual(mock_generate_all.call_args.args[0], Organization.BAKERY)

    def test_clear_doesNotGenerateAnything(self, mock_clear, mock_generate_all):
        call_command("populate", "--clear")

        mock_clear.assert_called_once()
        mock_generate_all.assert_not_called()
