from django.urls import reverse

from tapir.wirgarten.forms.pickup_location import PickupLocationEditForm
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

TEXT_LIMIT = 3000


def build_form_data(**overrides) -> dict:
    data = {
        "coords": "10.1,53.2",
        "name": "Test location",
        "street": "Test street 1",
        "postcode": "12345",
        "city": "Test city",
        "monday_times": "08:00-12:00",
    }
    data.update(overrides)
    return data


class TestPickupLocationEditFormTextLimits(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_modelFields_allowTextsAboveOldLimitOf1024(self):
        # Guards the migration: the DB column must really be as wide as the model says.
        pickup_location = PickupLocationFactory.create(
            info="i" * TEXT_LIMIT, route_info="r" * TEXT_LIMIT
        )

        pickup_location.refresh_from_db()

        self.assertEqual(TEXT_LIMIT, len(pickup_location.info))
        self.assertEqual(TEXT_LIMIT, len(pickup_location.route_info))

    def test_modelFields_maxLengthMatchesFormLimit(self):
        form = PickupLocationEditForm()

        for field_name in ["info", "route_info"]:
            with self.subTest(field_name=field_name):
                self.assertEqual(
                    TEXT_LIMIT,
                    PickupLocation._meta.get_field(field_name).max_length,
                )
                self.assertEqual(TEXT_LIMIT, form.fields[field_name].max_length)

    def test_widgets_haveMaxlengthAttribute(self):
        form = PickupLocationEditForm()

        for field_name in ["info", "route_info"]:
            with self.subTest(field_name=field_name):
                self.assertIn(f'maxlength="{TEXT_LIMIT}"', str(form[field_name]))

    def test_isValid_textsExactlyAtLimit_isValid(self):
        form = PickupLocationEditForm(
            build_form_data(info="i" * TEXT_LIMIT, route_info="r" * TEXT_LIMIT)
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_isValid_infoOverLimit_returnsReadableError(self):
        form = PickupLocationEditForm(build_form_data(info="i" * (TEXT_LIMIT + 1)))

        self.assertFalse(form.is_valid())
        self.assertEqual(["info"], list(form.errors.keys()))
        error = form.errors["info"][0]
        self.assertIn(str(TEXT_LIMIT), error)
        self.assertIn(str(TEXT_LIMIT + 1), error)

    def test_isValid_routeInfoOverLimit_returnsReadableError(self):
        form = PickupLocationEditForm(
            build_form_data(route_info="r" * (TEXT_LIMIT + 1))
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(["route_info"], list(form.errors.keys()))
        error = form.errors["route_info"][0]
        self.assertIn(str(TEXT_LIMIT), error)
        self.assertIn(str(TEXT_LIMIT + 1), error)

    def test_save_longInfoAndRouteInfo_arePersistedCompletely(self):
        info = "<p>" + "ä" * (TEXT_LIMIT - 7) + "</p>"
        route_info = "r" * TEXT_LIMIT
        form = PickupLocationEditForm(build_form_data(info=info, route_info=route_info))
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        pickup_location = PickupLocation.objects.get(name="Test location")
        self.assertEqual(info, pickup_location.info)
        self.assertEqual(route_info, pickup_location.route_info)

    def test_editView_infoOverLimit_rerendersFormWithErrorAndDoesNotSave(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        pickup_location = PickupLocationFactory.create(
            name="Test location", info="old info", coords_lon=10.1, coords_lat=53.2
        )

        response = self.client.post(
            reverse(
                "wirgarten:pickup_locations_edit", kwargs={"id": pickup_location.id}
            ),
            build_form_data(info="i" * (TEXT_LIMIT + 1)),
        )

        # 200 with the form again (instead of a 500) is what keeps the modal from
        # showing the generic "Ein Fehler ist aufgetreten" message.
        self.assertEqual(200, response.status_code)
        content = response.content.decode()
        self.assertIn("form-fields", content)
        self.assertIn(f"maximal {TEXT_LIMIT} Zeichen erlaubt", content)
        pickup_location.refresh_from_db()
        self.assertEqual("old info", pickup_location.info)

    def test_editView_infoBetweenOldAndNewLimit_isSaved(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        pickup_location = PickupLocationFactory.create(
            name="Test location", info="old info", coords_lon=10.1, coords_lat=53.2
        )
        new_info = "<p>" + "x" * 1200 + "</p>"

        response = self.client.post(
            reverse(
                "wirgarten:pickup_locations_edit", kwargs={"id": pickup_location.id}
            ),
            build_form_data(info=new_info),
        )

        self.assertEqual(200, response.status_code)
        self.assertNotIn("form-fields", response.content.decode())
        pickup_location.refresh_from_db()
        self.assertEqual(new_info, pickup_location.info)
