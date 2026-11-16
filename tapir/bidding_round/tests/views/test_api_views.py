import datetime
from decimal import Decimal
from unittest.mock import ANY, patch

from django.urls import reverse
from rest_framework import status

from tapir.associations.tests.factories import (
    AssociationMembershipFactory,
    AssociationMembershipTypeFactory,
    AssociationMembershipTypePriceFactory,
)
from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_CLOSED,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.bidding_round.tests.factories import BiddingRoundProductPriceFactory
from tapir.bidding_round.tests.helpers import (
    bid_payload,
    create_open_round,
    get_product_for_round,
    bid_range_payload,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.models import OrderFeedback
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class BiddingRoundApiTestBase(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _enable(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_BID_SHARES_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_BID_CAROUSEL_ENABLED, True)


class TestPublicDataView(BiddingRoundApiTestBase):
    def test_publicData_withoutActiveRound_reportsEnded(self):
        self._enable()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("ended", response.data["round_status"])
        self.assertIsNone(response.data["round"])

    def test_publicData_withBidSwitches_returnsTheirValues(self):
        self._enable()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTrue(response.data["bid_options"]["quantity_enabled"])
        self.assertTrue(response.data["bid_options"]["carousel_enabled"])

        self._set_parameter(ParameterKeys.BIDDING_ROUND_BID_SHARES_ENABLED, False)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_BID_CAROUSEL_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(response.data["bid_options"]["quantity_enabled"])
        self.assertFalse(response.data["bid_options"]["carousel_enabled"])

    def test_publicData_withMemberPickupLocation_returnsLocationAndCharge(self):
        self._enable()
        bidding_round = create_open_round()
        member = MemberFactory.create()
        pickup_location = PickupLocationFactory.create(name="Testhof")
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=bidding_round.growing_period.start_date
            - datetime.timedelta(days=1),
        )
        self.client.force_login(member)

        with patch.object(
            BiddingRoundDeliveryChargeService,
            "get_yearly_delivery_charge",
            return_value=Decimal("12.00"),
        ) as mock_charge:
            response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        location = response.data["current_pickup_location"]
        self.assertEqual("Testhof", location["name"])
        self.assertEqual("12.00", location["yearly_delivery_charge"])
        mock_charge.assert_called_once_with(
            pickup_location_id=pickup_location.id,
            product_type=bidding_round.product_types.first().product_type,
            growing_period=bidding_round.growing_period,
            cache=ANY,
        )

    def test_publicData_withoutPickupLocation_returnsNull(self):
        self._enable()
        create_open_round()
        self.client.force_login(MemberFactory.create())

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIsNone(response.data["current_pickup_location"])

    def test_publicData_withActiveRound_returnsRoundAndProduct(self):
        self._enable()
        create_open_round()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("active", response.data["round_status"])
        self.assertEqual(1, len(response.data["biddable_product"]["products"]))
        self.assertEqual(
            "90.00", response.data["biddable_product"]["products"][0]["reference_value"]
        )
        self.assertEqual("Gebot 1", response.data["texts"]["bid"]["level_1_label"])

    def test_publicData_includesProductImage(self):
        self._enable()
        bidding_round = create_open_round()
        product = get_product_for_round(bidding_round)
        product.url_of_image_in_bestellwizard = "https://example.com/share.png"
        product.save(update_fields=["url_of_image_in_bestellwizard"])

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            "https://example.com/share.png",
            response.data["biddable_product"]["products"][0]["image_url"],
        )

    def test_publicData_withMember_returnsSepaAndBankingData(self):
        self._enable()
        bidding_round = create_open_round()
        member = MemberFactory.create(
            account_owner="Test Owner", iban="DE89370400440532013000"
        )
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.QUARTERLY,
            valid_from=bidding_round.growing_period.start_date,
        )
        self.client.force_login(member)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTrue(response.data["sepa_enabled"])
        self.assertEqual("Test Owner", response.data["account_owner"])
        self.assertEqual("DE89370400440532013000", response.data["iban"])
        self.assertEqual("quarterly", response.data["payment_rhythm"])

    def test_publicData_withMember_returnsFirstName(self):
        self._enable()
        create_open_round()
        member = MemberFactory.create(first_name="Jana")
        self.client.force_login(member)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("Jana", response.data["first_name"])

    def test_publicData_anonymous_returnsNoFirstName(self):
        self._enable()
        create_open_round()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIsNone(response.data["first_name"])

    def test_publicData_withActiveAssociationMembership_returnsNameAndPrice(self):
        self._enable()
        bidding_round = create_open_round()
        membership_type = AssociationMembershipTypeFactory.create(name="Fördermitglied")
        AssociationMembershipTypePriceFactory.create(
            type=membership_type,
            valid_from=bidding_round.growing_period.start_date,
            price=Decimal("12.00"),
        )
        member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            type=membership_type,
            start_date=bidding_round.growing_period.start_date,
            end_date=None,
        )
        self.client.force_login(member)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {"name": "Fördermitglied", "price": "12.00"},
            response.data["association_membership"],
        )

    def test_publicData_withoutActiveAssociationMembership_returnsNull(self):
        self._enable()
        bidding_round = create_open_round()
        membership_type = AssociationMembershipTypeFactory.create()
        member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            type=membership_type,
            start_date=bidding_round.growing_period.start_date
            - datetime.timedelta(days=100),
            end_date=bidding_round.growing_period.start_date
            - datetime.timedelta(days=1),
        )
        self.client.force_login(member)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIsNone(response.data["association_membership"])

    def test_publicData_feedbackEnabledByDefault(self):
        self._enable()
        create_open_round()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTrue(response.data["feedback_enabled"])

    def test_publicData_feedbackDisabled_returnsFalse(self):
        self._enable()
        create_open_round()
        self._set_parameter(ParameterKeys.BIDDING_ROUND_FEEDBACK_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(response.data["feedback_enabled"])

    def test_publicData_textsContainPersonalizedSummaryTitleAndFinalSubmitLabel(
        self,
    ):
        self._enable()
        create_open_round()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            "{vorname}, hier nochmal dein Gebot auf einen Blick",
            response.data["texts"]["summary_title"],
        )
        self.assertEqual(
            "Gebot kostenpflichtig abgeben",
            response.data["texts"]["final_submit_label"],
        )

    def test_publicData_bidOptionsDefaultToOff(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, True)
        create_open_round()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(response.data["bid_options"]["quantity_enabled"])
        self.assertFalse(response.data["bid_options"]["carousel_enabled"])

    def test_publicData_bidOptionsEnabled_returnsTrue(self):
        self._enable()
        create_open_round()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTrue(response.data["bid_options"]["quantity_enabled"])
        self.assertTrue(response.data["bid_options"]["carousel_enabled"])


class TestMemberBidView(BiddingRoundApiTestBase):
    def test_get_anonymous_returns403(self):
        self._enable()
        bidding_round = create_open_round()

        response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_validBid_storesBid(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_payload(bidding_round, quantity=2),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        get_response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        )
        self.assertStatusCode(get_response, status.HTTP_200_OK)
        item = get_response.data["bid"]["items"][0]
        self.assertEqual("80.00", item["amount_1"])
        self.assertEqual(2, item["quantity"])
        self.assertEqual("1920.00", item["amount_per_year"])
        self.assertEqual("1920.00", get_response.data["bid"]["total_per_year"])

    def test_post_bidRangeBid_storesTwoAmounts(self):
        self._enable()
        bidding_round = create_open_round(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        self.client.force_login(MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_range_payload(bidding_round, quantity=2),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        item = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        ).data["bid"]["items"][0]
        self.assertEqual("70.00", item["amount_1"])
        self.assertEqual("90.00", item["amount_2"])
        self.assertIsNone(item["amount_3"])
        self.assertEqual(2, item["quantity"])

    def test_post_quantityOutOfRange_returns400(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_payload(bidding_round, quantity=6),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_get_withExistingSubscription_returnsCurrentQuantity(self):
        self._enable()
        bidding_round = create_open_round()
        member = MemberFactory.create()
        self.client.force_login(member)
        SubscriptionFactory.create(
            member=member,
            product=get_product_for_round(bidding_round),
            period=bidding_round.growing_period,
            quantity=2,
            start_date=bidding_round.growing_period.start_date,
            end_date=bidding_round.growing_period.end_date,
        )

        response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            2,
            response.data["biddable_product"]["products"][0]["current_quantity"],
        )

    def test_post_amountBelowMinimum_returns400(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_payload(bidding_round, amount="10.00"),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_post_withSepaAndPrivacyData_updatesMemberAndSetsConsents(self):
        self._enable()
        bidding_round = create_open_round()
        member = MemberFactory.create(
            account_owner=None,
            iban=None,
            sepa_consent=None,
            withdrawal_consent=None,
            privacy_consent=None,
        )
        self.client.force_login(member)
        payload = bid_payload(bidding_round, amount="80.00")
        payload.update(
            {
                "sepa_allowed": True,
                "account_owner": "Neue Inhaberin",
                "iban": "DE89370400440532013000",
                "payment_rhythm": "monthly",
                "privacy_policy_read": True,
                "cancellation_policy_read": True,
                "contract_accepted": True,
            }
        )

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=payload,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        member.refresh_from_db()
        self.assertEqual("Neue Inhaberin", member.account_owner)
        self.assertEqual("DE89370400440532013000", member.iban)
        self.assertIsNotNone(member.sepa_consent)
        self.assertIsNotNone(member.withdrawal_consent)
        self.assertIsNotNone(member.privacy_consent)
        self.assertEqual(
            "monthly",
            MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member,
                reference_date=bidding_round.growing_period.start_date,
                cache={},
            ),
        )

    def test_post_withoutPrivacyConsent_returns400(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())
        payload = bid_payload(bidding_round, amount="80.00")
        payload["privacy_policy_read"] = False

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=payload,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            "Die Datenschutzerklärung muss akzeptiert sein.", response.data["error"]
        )

    def test_post_withoutCancellationPolicyRead_returns400(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())
        payload = bid_payload(bidding_round, amount="80.00")
        payload["cancellation_policy_read"] = False

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=payload,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            "Die Widerrufsbelehrung muss akzeptiert sein.", response.data["error"]
        )

    def test_post_withoutContractAccepted_returns400(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())
        payload = bid_payload(bidding_round, amount="80.00")
        payload["contract_accepted"] = False

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=payload,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            "Vertragsgrundsätze müssen akzeptiert sein.", response.data["error"]
        )

    def test_post_withSepaAllowedButWithoutIban_returns400(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create(iban=None))
        payload = bid_payload(bidding_round, amount="80.00")
        payload["sepa_allowed"] = True
        payload["iban"] = ""

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=payload,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            "Für die SEPA-Zustimmung wird eine IBAN benötigt.", response.data["error"]
        )

    def test_post_withFeedback_createsOrderFeedback(self):
        self._enable()
        bidding_round = create_open_round()
        member = MemberFactory.create()
        self.client.force_login(member)
        payload = bid_payload(bidding_round, amount="80.00")
        payload["feedback"] = "Tolles Angebot!"

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=payload,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        feedback_entries = OrderFeedback.objects.filter(member=member)
        self.assertEqual(1, feedback_entries.count())
        self.assertEqual("Tolles Angebot!", feedback_entries.first().feedback_text)

    def test_post_withFeedbackTwice_updatesTheSameFeedback(self):
        self._enable()
        bidding_round = create_open_round()
        member = MemberFactory.create()
        self.client.force_login(member)
        payload = bid_payload(bidding_round, amount="80.00")

        for feedback in ("Erstes Feedback", "Zweites Feedback"):
            payload["feedback"] = feedback
            response = self.client.post(
                reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
                data=payload,
                content_type="application/json",
            )
            self.assertStatusCode(response, status.HTTP_200_OK)

        feedback_entries = OrderFeedback.objects.filter(
            member=member, bidding_round=bidding_round
        )
        self.assertEqual(1, feedback_entries.count())
        self.assertEqual("Zweites Feedback", feedback_entries.get().feedback_text)

    def test_post_withoutFeedback_createsNoOrderFeedback(self):
        self._enable()
        bidding_round = create_open_round()
        member = MemberFactory.create()
        self.client.force_login(member)
        payload = bid_payload(bidding_round, amount="80.00")
        payload["feedback"] = ""

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=payload,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(OrderFeedback.objects.filter(member=member).exists())


class TestRoundAdminViews(BiddingRoundApiTestBase):
    def setUp(self):
        super().setUp()
        self._enable()
        self.client.force_login(MemberFactory.create(is_superuser=True, is_staff=True))

    def test_listAndCreate_returnsRound(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()

        create_response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "end_at": (get_now(cache={}) + datetime.timedelta(days=1)).isoformat(),
                "product_type_id": product_type.id,
                "target_amount_per_year": "1000.00",
            },
            content_type="application/json",
        )

        self.assertStatusCode(create_response, status.HTTP_201_CREATED)
        list_response = self.client.get(reverse("bidding_rounds:round_list_create"))
        self.assertStatusCode(list_response, status.HTTP_200_OK)
        self.assertEqual(1, len(list_response.data))

    def test_startCloseAndResults(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name="Beitragsrunde Test",
            end_at=get_now(cache={}) + datetime.timedelta(days=1),
            product_type_id=product_type.id,
            target_amount_per_year="1000.00",
            cache={},
        )
        round_product_type = bidding_round.product_types.get()
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=ProductFactory.create(type=product_type),
        )

        start_response = self.client.post(
            reverse("bidding_rounds:round_start", args=[bidding_round.id])
        )
        self.assertStatusCode(start_response, status.HTTP_200_OK)
        self.assertEqual("active", start_response.data["status"])

        close_response = self.client.post(
            reverse("bidding_rounds:round_close", args=[bidding_round.id])
        )
        self.assertStatusCode(close_response, status.HTTP_200_OK)

        results_response = self.client.get(
            reverse("bidding_rounds:round_results", args=[bidding_round.id])
        )
        self.assertStatusCode(results_response, status.HTTP_200_OK)
        self.assertEqual("1000.00", results_response.data["target_per_year"])
        self.assertEqual(0, results_response.data["bidder_count"])


class TestPublicResultsView(BiddingRoundApiTestBase):
    def test_inactiveRound_returns404(self):
        self._enable()
        bidding_round = create_open_round()
        bidding_round.status = BIDDING_ROUND_STATUS_CLOSED
        bidding_round.save()

        response = self.client.get(
            reverse("bidding_rounds:public_results", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_activeRound_returnsAggregates(self):
        self._enable()
        bidding_round = create_open_round()
        ProductCapacityFactory.create(
            period=bidding_round.growing_period,
            product_type=bidding_round.product_types.first().product_type,
            capacity=100,
        )
        member = MemberFactory.create()
        self.client.force_login(member)
        self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_payload(bidding_round, amount="80.00"),
            content_type="application/json",
        )

        response = self.client.get(
            reverse("bidding_rounds:public_results", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("1000.00", response.data["target_per_year"])
        self.assertEqual(96.0, response.data["coverage_percent"])
        self.assertEqual("yellow", response.data["coverage_status"])
        self.assertEqual("100.00", response.data["capacity_shares"])
        self.assertEqual(Decimal("1"), Decimal(response.data["current_shares"]))
        self.assertEqual(1.0, response.data["utilization_percent"])
        self.assertEqual(96.0, response.data["levels"]["yellow"]["coverage_percent"])


class TestAdminBidTools(BiddingRoundApiTestBase):
    def setUp(self):
        super().setUp()
        self._enable()
        self.client.force_login(MemberFactory.create(is_superuser=True, is_staff=True))

    def test_adminBidFlow(self):
        bidding_round = create_open_round()
        product = get_product_for_round(bidding_round)
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            product=product,
            period=bidding_round.growing_period,
            quantity=1,
            start_date=bidding_round.growing_period.start_date,
            end_date=bidding_round.growing_period.end_date,
        )

        without_bid = self.client.get(
            reverse("bidding_rounds:members_without_bid", args=[bidding_round.id])
        )
        self.assertStatusCode(without_bid, status.HTTP_200_OK)
        self.assertIn(member.id, [entry["id"] for entry in without_bid.data])

        create_response = self.client.post(
            reverse("bidding_rounds:bid_create", args=[bidding_round.id]),
            data={
                "member_id": member.id,
                "items": [
                    {
                        "round_product_type_id": bidding_round.product_types.first().id,
                        "product_id": product.id,
                        "quantity": 2,
                        "amount_1": "80.00",
                    }
                ],
                "admin_confirmed": True,
            },
            content_type="application/json",
        )
        self.assertStatusCode(create_response, status.HTTP_201_CREATED)
        self.assertEqual(2, create_response.data["items"][0]["quantity"])
        self.assertTrue(create_response.data["entered_by_admin"])
        self.assertIsNotNone(create_response.data["admin_confirmed"])
        bid_id = create_response.data["id"]

        confirm_response = self.client.post(
            reverse("bidding_rounds:confirm_bids", args=[bidding_round.id]),
            data={"bid_ids": [bid_id]},
            content_type="application/json",
        )
        self.assertStatusCode(confirm_response, status.HTTP_200_OK)
        self.assertEqual(0, confirm_response.data["unconfirmed_bid_count"])

        bidding_round.status = BIDDING_ROUND_STATUS_CLOSED
        bidding_round.save()

        lock_response = self.client.post(
            reverse("bidding_rounds:lock_average_bid", args=[bidding_round.id]),
            data={"position": 0, "surcharge_percent": 0},
            content_type="application/json",
        )
        self.assertStatusCode(lock_response, status.HTTP_200_OK)
        self.assertIsNotNone(lock_response.data["average_bid_locked_at"])

        results_response = self.client.get(
            reverse("bidding_rounds:round_results", args=[bidding_round.id])
        )
        self.assertStatusCode(results_response, status.HTTP_200_OK)
        self.assertEqual(0, results_response.data["unconfirmed_bid_count"])

        csv_response = self.client.get(
            reverse("bidding_rounds:export_csv", args=[bidding_round.id])
        )
        self.assertStatusCode(csv_response, status.HTTP_200_OK)
        csv_content = csv_response.content.decode("utf-8")
        self.assertIn("Mitglied", csv_content)
        self.assertIn("Anteile", csv_content)
        self.assertIn("Betrag / Monat", csv_content)
        self.assertIn("Betrag / Jahr", csv_content)
        self.assertIn("160.00", csv_content)
        self.assertIn("1920.00", csv_content)

        edit_response = self.client.patch(
            reverse("bidding_rounds:bid_edit", args=[bidding_round.id, bid_id]),
            data={
                "items": [
                    {
                        "round_product_type_id": bidding_round.product_types.first().id,
                        "product_id": product.id,
                        "quantity": 2,
                        "amount_1": "85.00",
                    }
                ]
            },
            content_type="application/json",
        )
        self.assertStatusCode(edit_response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Durchschnittsgebot", edit_response.data["error"])

        delete_response = self.client.delete(
            reverse("bidding_rounds:bid_edit", args=[bidding_round.id, bid_id])
        )
        self.assertStatusCode(delete_response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Durchschnittsgebot", delete_response.data["error"])

    def test_create_withoutItems_returns400(self):
        bidding_round = create_open_round()
        member = MemberFactory.create()

        response = self.client.post(
            reverse("bidding_rounds:bid_create", args=[bidding_round.id]),
            data={"member_id": member.id},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
