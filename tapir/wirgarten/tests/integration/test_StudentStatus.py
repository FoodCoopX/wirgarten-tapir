import datetime

from django.template.response import TemplateResponse
from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import (
    Member,
    Subscription,
    ProductCapacity,
    GrowingPeriod,
    MemberPickupLocation,
)
from tapir.wirgarten.parameters import (
    ParameterDefinitions,
    Parameter,
)
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductCapacityFactory,
    ProductPriceFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestStudentStatus(TapirIntegrationTest):
    def setUp(self):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(
            key=Parameter.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES
        ).update(value="True")
        configure_mail_module()

    def test_cooperativeShareForm_fromTheMemberProfile_doesntShowStudentStatusField(
        self,
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        url = reverse("wirgarten:member_add_coop_shares", args=[member.id])
        response: TemplateResponse = self.client.get(
            url,
        )

        form_fields = response.context_data["form"].fields
        self.assertNotIn("is_student", form_fields.keys())

    def test_cooperativeShareForm_fromTheRegistrationWizard_showsStudentStatusField(
        self,
    ):
        response: TemplateResponse = self.client.get("/wirgarten/register")

        form_fields = response.context_data["form"].fields
        self.assertIn("is_student", form_fields.keys())

    def test_cooperativeShareForm_addSharesAsStudent_canAddLessThanTheMinimum(
        self,
    ):
        member: Member = MemberFactory.create(is_student=True)
        self.assertEqual(0, member.coop_shares_quantity)
        self.client.force_login(member)

        url = reverse("wirgarten:member_add_coop_shares", args=[member.id])
        data = {
            "cooperative_shares": 50,
            "statute_consent": True,
        }
        response = self.client.post(url, data)

        self.assertStatusCode(response, 200)
        self.assertEqual(1, member.coop_shares_quantity)

    def test_cooperativeShareForm_addZeroSharesAsStudent_formError(
        self,
    ):
        member: Member = MemberFactory.create(is_student=True)
        self.assertEqual(0, member.coop_shares_quantity)
        self.client.force_login(member)

        url = reverse("wirgarten:member_add_coop_shares", args=[member.id])
        data = {
            "cooperative_shares": 0,
            "statute_consent": True,
        }
        response: TemplateResponse = self.client.post(url, data)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, member.coop_shares_quantity)
        form_errors = response.context_data["form"].errors
        self.assertIn("cooperative_shares", form_errors.keys())

    def test_baseProductForm_asStudent_canAddSubscriptionWithoutShares(
        self,
    ):
        member: Member = MemberFactory.create(is_student=True)
        now = datetime.datetime(year=2023, month=6, day=12)
        mock_timezone(self, now)
        product_capacity: ProductCapacity = ProductCapacityFactory.create(
            capacity=1000,
            product_type__name="Ernteanteile",
            product_type__delivery_cycle=WEEKLY[0],
        )
        growing_period = GrowingPeriod.objects.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )

        parameter = TapirParameter.objects.get(key=Parameter.COOP_BASE_PRODUCT_TYPE)
        parameter.value = product_capacity.product_type.id
        parameter.save()

        ProductPriceFactory.create(
            product__type=product_capacity.product_type,
            product__name="M",
            price=50,
            valid_from=datetime.date(year=2023, month=1, day=1),
        )

        member_pickup_location: MemberPickupLocation = (
            MemberPickupLocationFactory.create(member=member)
        )
        PickupLocationCapabilityFactory.create(
            product_type=product_capacity.product_type,
            pickup_location=member_pickup_location.pickup_location,
        )
        member_subscriptions = Subscription.objects.filter(
            member=member,
        )
        self.assertEqual(0, member.coop_shares_quantity)
        self.assertFalse(member_subscriptions.exists())
        self.client.force_login(member)

        url = (
            reverse("wirgarten:member_add_subscription", args=[member.id])
            + "?productType=Ernteanteile"
        )
        data = {
            "growing_period": growing_period.id,
            "base_product_M": 1,
            "solidarity_price_harvest_shares": 0.0,
        }
        self.client.post(url, data)

        self.assertEqual(1, member_subscriptions.count())

    def test_personalDataFormForm_loggedInAsNormalMember_studentStatusCheckboxDisabled(
        self,
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        url = reverse("wirgarten:member_edit", args=[member.id])
        response: TemplateResponse = self.client.get(url)

        form_fields = response.context_data["form"].fields
        self.assertIn("is_student", form_fields.keys())
        self.assertTrue(form_fields["is_student"].disabled)

    def test_personalDataFormForm_loggedInAsAdmin_studentStatusCheckboxEnabled(
        self,
    ):
        member_to_edit = MemberFactory.create()
        member_logged_in: Member = MemberFactory.create(is_superuser=True)

        self.client.force_login(member_logged_in)

        url = reverse("wirgarten:member_edit", args=[member_to_edit.id])
        response: TemplateResponse = self.client.get(url)

        form_fields = response.context_data["form"].fields
        self.assertIn("is_student", form_fields.keys())
        self.assertFalse(form_fields["is_student"].disabled)
