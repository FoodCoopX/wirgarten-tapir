from unittest.mock import Mock, patch

from allauth.socialaccount.models import SocialAccount
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import RequestFactory
from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.accounts.models import TapirUser, UpdateTapirUserLogEntry
from tapir.coop.models import RetiredMemberNumber
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.member_importer import MemberImporter
from tapir.wirgarten.forms.member_number import AdminMemberCreationForm
from tapir.wirgarten.models import Member, MandateReference, Payment, Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MandateReferenceFactory,
    PaymentFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.views.member.list.modals import save_member_and_assign_number


class TestManualMemberNumbers(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.admin = self._login_as_admin()
        patcher = patch.object(TransactionalTrigger, "fire_action")
        self.fire_action = patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def creation_data(email="synthetic@number-test.invalid", number=""):
        return {
            "first_name": "Synthetic",
            "last_name": "Member",
            "email": email,
            "phone_number": "+4917744563327",
            "street": "Teststraße 1",
            "street_2": "",
            "postcode": "12345",
            "city": "Teststadt",
            "country": "DE",
            "birthdate": "1980-01-01",
            "member_no": number,
        }

    def creation_form(self, email, number):
        request = RequestFactory().post("/")
        request.user = self.admin
        form = AdminMemberCreationForm(
            self.creation_data(email, number), request=request
        )
        self.assertTrue(form.is_valid(), form.errors)
        return form

    def test_create_explicitNumber_isUsedAndAuditedWithoutMailOrPayment(self):
        response = self.client.post(
            reverse("wirgarten:member_create"), self.creation_data(number=9001)
        )
        self.assertStatusCode(response, 200)
        self.assertTemplateUsed(
            response, "wirgarten/generic/modal/form-modal-redirect.html"
        )
        member = Member.objects.get(email="synthetic@number-test.invalid")
        self.assertEqual(9001, member.member_no)
        self.assertIsNotNone(member.keycloak_id)
        entry = UpdateTapirUserLogEntry.objects.get(user=member)
        self.assertEqual(self.admin.pk, entry.actor_id)
        self.assertEqual({"member_no": "None"}, entry.old_values)
        self.assertEqual({"member_no": "9001"}, entry.new_values)
        self.fire_action.assert_not_called()
        self.mock_keycloak_client.send_verify_email.assert_not_called()
        self.mock_keycloak_client.send_update_account.assert_not_called()
        self.assertFalse(Payment.objects.exists())
        self.assertEqual([], mail.outbox)

    def test_create_omittedNumber_keepsAutomaticAllocation(self):
        expected = MemberNumberService.compute_next_member_number(cache={})
        data = self.creation_data()
        data.pop("member_no")
        response = self.client.post(reverse("wirgarten:member_create"), data)
        self.assertStatusCode(response, 200)
        self.assertEqual(expected, Member.objects.get(email=data["email"]).member_no)

    def test_create_duplicateNumber_showsFieldErrorWithoutPartialCreation(self):
        MemberFactory.create(member_no=9001)
        before = (Member.objects.count(), TapirUser.objects.count())
        self.mock_keycloak_client.reset_mock()
        response = self.client.post(
            reverse("wirgarten:member_create"), self.creation_data(number=9001)
        )
        self.assertContains(response, MemberNumberService.DUPLICATE_NUMBER_MESSAGE)
        self.assertIn("member_no", response.context["form"].errors)
        self.assertEqual(before, (Member.objects.count(), TapirUser.objects.count()))
        self.mock_keycloak_client.create_user.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    def test_create_twoPrevalidatedFormsConflict_secondIsFullyRolledBack(self):
        first = self.creation_form("first@number-test.invalid", 9001)
        second = self.creation_form("second@number-test.invalid", 9001)
        save_member_and_assign_number(first)
        before = (Member.objects.count(), TapirUser.objects.count())
        self.mock_keycloak_client.reset_mock()
        with patch.object(MemberNumberService, "validate_member_number_available"):
            with self.assertRaises(ValidationError):
                save_member_and_assign_number(second)
        self.assertEqual(before, (Member.objects.count(), TapirUser.objects.count()))
        self.assertFalse(
            Member.objects.filter(email=second.cleaned_data["email"]).exists()
        )
        self.mock_keycloak_client.create_user.assert_not_called()
        self.assertEqual(1, UpdateTapirUserLogEntry.objects.count())

    def test_create_usernameRaceWithUnnumberedMember_isNotNumberConflict(self):
        form = self.creation_form("race@number-test.invalid", "")
        other = MemberFactory.create(
            username=form.cleaned_data["email"], email="other@number-test.invalid"
        )
        Member.objects.filter(pk=other.pk).update(member_no=None)
        self.mock_keycloak_client.reset_mock()
        with self.assertRaises(IntegrityError):
            save_member_and_assign_number(form)
        self.assertFalse(
            Member.objects.filter(email=form.cleaned_data["email"]).exists()
        )
        self.mock_keycloak_client.create_user.assert_not_called()

    def test_correct_changesOnlyNumberAndAuditsActorWithoutExternalEffects(self):
        member = MemberFactory.create(member_no=17, keycloak_id="synthetic-kc-id")
        SocialAccount.objects.create(
            user=member, provider="keycloak", uid=member.keycloak_id
        )
        mandate = MandateReferenceFactory.create(member=member, ref="LEGACY-17")
        SubscriptionFactory.create(member=member, mandate_ref=mandate)
        PaymentFactory.create(mandate_ref=mandate)
        before = Member.objects.values().get(pk=member.pk)
        related_before = {
            "contracts": list(Subscription.objects.values()),
            "mandates": list(MandateReference.objects.values()),
            "payments": list(Payment.objects.values()),
            "social": list(SocialAccount.objects.values()),
        }
        self.mock_keycloak_client.reset_mock()
        response = self.client.post(
            reverse("wirgarten:member_number_edit", args=[member.pk]),
            {"member_no": 9001},
        )
        self.assertTemplateUsed(
            response, "wirgarten/generic/modal/form-modal-redirect.html"
        )
        after = Member.objects.values().get(pk=member.pk)
        self.assertEqual(17, before.pop("member_no"))
        self.assertEqual(9001, after.pop("member_no"))
        self.assertEqual(before, after)
        self.assertEqual(
            related_before["contracts"], list(Subscription.objects.values())
        )
        self.assertEqual(
            related_before["mandates"], list(MandateReference.objects.values())
        )
        self.assertEqual(related_before["payments"], list(Payment.objects.values()))
        self.assertEqual(related_before["social"], list(SocialAccount.objects.values()))
        member.refresh_from_db()
        self.assertEqual(
            mandate.pk,
            MandateReferenceProvider.get_or_create_mandate_reference(
                member, cache={}
            ).pk,
        )
        entry = UpdateTapirUserLogEntry.objects.get(user=member)
        self.assertEqual(self.admin.pk, entry.actor_id)
        self.assertEqual({"member_no": "17"}, entry.old_values)
        self.assertEqual({"member_no": "9001"}, entry.new_values)
        self.mock_keycloak_client.assert_not_called()
        self.assertEqual([], self.mock_keycloak_client.mock_calls)
        self.fire_action.assert_not_called()
        self.assertEqual([], mail.outbox)

    def test_correct_duplicate_showsFieldErrorAndChangesNothing(self):
        member = MemberFactory.create(member_no=17)
        MemberFactory.create(member_no=9001)
        response = self.client.post(
            reverse("wirgarten:member_number_edit", args=[member.pk]),
            {"member_no": 9001},
        )
        self.assertContains(response, MemberNumberService.DUPLICATE_NUMBER_MESSAGE)
        member.refresh_from_db()
        self.assertEqual(17, member.member_no)
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    def test_correct_highestNumberDownward_preservesMandateAndSkipsOldNumber(self):
        member = MemberFactory.create(member_no=9001)
        mandate = MandateReferenceFactory.create(member=member, ref="9001")
        before = MandateReference.objects.values().get(pk=mandate.pk)

        MemberNumberService.set_member_number(member, 17, actor=self.admin)
        response = self.client.post(
            reverse("wirgarten:member_create"), self.creation_data()
        )

        self.assertTemplateUsed(
            response, "wirgarten/generic/modal/form-modal-redirect.html"
        )
        self.assertEqual(
            9002, Member.objects.get(email=self.creation_data()["email"]).member_no
        )
        self.assertEqual(before, MandateReference.objects.values().get(pk=mandate.pk))
        self.assertEqual(
            mandate.pk,
            MandateReferenceProvider.get_or_create_mandate_reference(
                member, cache={}
            ).pk,
        )

    def test_retiredNumber_cannotBeAssignedToAnotherMember(self):
        member = MemberFactory.create(member_no=9001)
        other = MemberFactory.create(member_no=18)
        MemberNumberService.set_member_number(member, 17, actor=self.admin)

        response = self.client.post(
            reverse("wirgarten:member_create"), self.creation_data(number=9001)
        )
        self.assertContains(response, MemberNumberService.RETIRED_NUMBER_MESSAGE)
        response = self.client.post(
            reverse("wirgarten:member_number_edit", args=[other.pk]),
            {"member_no": 9001},
        )
        self.assertContains(response, MemberNumberService.RETIRED_NUMBER_MESSAGE)
        with self.assertRaisesMessage(
            TapirDataImportException, str(MemberNumberService.RETIRED_NUMBER_MESSAGE)
        ):
            MemberImporter.import_member(
                {"Nr": "9001"}, update_existing=True, dry_run=False, stdout=Mock()
            )

        self.assertFalse(Member.objects.filter(member_no=9001).exists())
        other.refresh_from_db()
        self.assertEqual(18, other.member_no)
        self.mock_keycloak_client.create_user.assert_not_called()

    def test_correct_originalMemberCanReclaimRetiredNumber(self):
        member = MemberFactory.create(member_no=9001)
        MemberNumberService.set_member_number(member, 17, actor=self.admin)

        self.assertTrue(
            MemberNumberService.set_member_number(member, 9001, actor=self.admin)
        )
        member.refresh_from_db()
        self.assertEqual(9001, member.member_no)

    def test_correct_databaseUniqueConflict_isTranslatedAfterRollback(self):
        member = MemberFactory.create(member_no=17)
        MemberFactory.create(member_no=9001)
        with patch.object(MemberNumberService, "validate_member_number_available"):
            with self.assertRaises(ValidationError) as caught:
                MemberNumberService.set_member_number(member, 9001, actor=self.admin)
        self.assertIn("member_no", caught.exception.message_dict)
        member.refresh_from_db()
        self.assertEqual(17, member.member_no)
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    def test_correct_auditFailure_rollsBackNumber(self):
        member = MemberFactory.create(member_no=17)
        with patch.object(UpdateTapirUserLogEntry, "save", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                MemberNumberService.set_member_number(member, 9001, actor=self.admin)
        member.refresh_from_db()
        self.assertEqual(17, member.member_no)
        self.assertFalse(RetiredMemberNumber.objects.filter(number=17).exists())

    def test_correct_unchangedNumber_doesNotWriteAuditEntry(self):
        member = MemberFactory.create(member_no=17)
        self.client.post(
            reverse("wirgarten:member_number_edit", args=[member.pk]), {"member_no": 17}
        )
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    def test_correct_memberCannotChangeOwnOrAnotherMembersNumber(self):
        member = MemberFactory.create(is_superuser=False, member_no=17)
        other = MemberFactory.create(member_no=18)
        self.client.force_login(member)
        for target in [member, other]:
            for method in [self.client.get, self.client.post]:
                response = method(
                    reverse("wirgarten:member_number_edit", args=[target.pk]),
                    {"member_no": 9001},
                )
                self.assertStatusCode(response, 403)
        member.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(17, member.member_no)
        self.assertEqual(18, other.member_no)
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())
        self.fire_action.assert_not_called()

    def test_create_memberCannotUseAdminCreationForm(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        response = self.client.post(
            reverse("wirgarten:member_create"), self.creation_data(number=9001)
        )
        self.assertEqual(302, response.status_code)
        self.assertFalse(
            Member.objects.filter(email="synthetic@number-test.invalid").exists()
        )

    def test_correct_invalidNumbers_areRejected(self):
        member = MemberFactory.create(member_no=17)
        for number in ["", "abc", "-1", "0", "2147483648"]:
            response = self.client.post(
                reverse("wirgarten:member_number_edit", args=[member.pk]),
                {"member_no": number},
            )
            self.assertIn("member_no", response.context["form"].errors)
        member.refresh_from_db()
        self.assertEqual(17, member.member_no)
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    def test_create_lateValidationError_isShownAndRollsBackNewAccount(self):
        before = (Member.objects.count(), TapirUser.objects.count())
        self.mock_keycloak_client.reset_mock()
        with patch.object(
            MemberNumberService,
            "set_member_number",
            side_effect=ValidationError(
                {"member_no": MemberNumberService.DUPLICATE_NUMBER_MESSAGE}
            ),
        ):
            response = self.client.post(
                reverse("wirgarten:member_create"), self.creation_data(number=9001)
            )
        self.assertContains(response, MemberNumberService.DUPLICATE_NUMBER_MESSAGE)
        self.assertEqual(before, (Member.objects.count(), TapirUser.objects.count()))
        self.mock_keycloak_client.create_user.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    def test_correct_lateValidationError_isShownInTheForm(self):
        member = MemberFactory.create(member_no=17)
        with patch.object(
            MemberNumberService,
            "set_member_number",
            side_effect=ValidationError(
                {"member_no": MemberNumberService.DUPLICATE_NUMBER_MESSAGE}
            ),
        ):
            response = self.client.post(
                reverse("wirgarten:member_number_edit", args=[member.pk]),
                {"member_no": 9001},
            )
        self.assertContains(response, MemberNumberService.DUPLICATE_NUMBER_MESSAGE)
        member.refresh_from_db()
        self.assertEqual(17, member.member_no)

    def test_sharedModal_validationErrorsStillPropagateUnlessOptedIn(self):
        from tapir.wirgarten.forms.member_number import MemberNumberForm
        from tapir.wirgarten.views.modal import get_form_modal

        member = MemberFactory.create(member_no=17)
        request = RequestFactory().post("/", {"member_no": 9001})
        with self.assertRaises(ValidationError):
            get_form_modal(
                request=request,
                form_class=MemberNumberForm,
                instance=member,
                handler=Mock(side_effect=ValidationError("unchanged behavior")),
            )
