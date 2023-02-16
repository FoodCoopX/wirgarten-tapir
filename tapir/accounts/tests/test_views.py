# FIXME
# from django_webtest import WebTest
# from django.contrib.auth import get_user_model
# from tapir.wirgarten.factories import (
#    MemberFactory,
#    ShareOwnershipFactory,
#    SubscriptionFactory,
#    PaymentFactory,
# )
# from tapir.utils.tests_utils import KeycloakTestCase
# from tapir.wirgarten.constants import Permission
# from django.urls import reverse
#
# User = get_user_model()
#
#
# class PermissionsTests( KeycloakTestCase, WebTest):
#
#    def test_user_edit_only_available_with_proper_perm(self):
#        member = ShareOwnershipFactory().member
#        user = self.create_user()
#        self.assertFalse(user.has_perm("accounts.manage"))
#        url = reverse("wirgarten:member_detail", kwargs={"pk": member.pk})
#        r = self.app.get(url, user=user, status=403)
#
#        selector = "#tapir_user_edit_button"
#        user.add_perm("accounts.manage")
#        self.assertTrue(user.has_perm("accounts.manage"))
#        r = self.app.get(url, user=user)
#        self.assertIsNotNone(r.html.select_one(selector))
#
#    def test_edit_payment_form_only_available_with_proper_perm(self):
#        member = SubscriptionFactory().member
#        p = PaymentFactory(mandate_ref__member=member)
#        user = self.create_user()
#        self.assertFalse(user.has_perm("coop.manage"))
#        url = reverse("wirgarten:member_payments", kwargs={"pk": member.pk})
#        r = self.app.get(url, user=user, status=403)
#
#        selector = "#edit-payment-form"
#        user.add_perm("coop.manage")
#        self.assertTrue(user.has_perm("coop.manage"))
#        r = self.app.get(url, user=user)
#        self.assertIsNotNone(r.html.select_one(selector))
#
#    def test_member_edit_button_only_available_with_proper_perm(self):
#        member = MemberFactory()
#        user = self.create_user()
#        self.assertFalse(user.has_perm("accounts.manage"))
#        url = reverse("wirgarten:member_list")
#        r = self.app.get(url, user=user, status=403)
#
#        selector = "#edit-member-details-btn"
#        user.add_perm("accounts.manage")
#        self.assertTrue(user.has_perm("accounts.manage"))
#        r = self.app.get(url, user=user)
#        self.assertIsNotNone(r.html.select_one(selector))
#
#    def test_trans_coop_shares_button_only_available_with_proper_perm(self):
#        member = MemberFactory()
#        user = self.create_user()
#        self.assertFalse(user.has_perm("coop.manage"))
#        url = reverse("wirgarten:member_list")
#        r = self.app.get(url, user=user, status=403)
#
#        selector = "#trans-coop-shares-btn"
#        user.add_perm("accounts.manage")
#        self.assertTrue(user.has_perm("coop.manage"))
#        r = self.app.get(url, user=user)
#        self.assertIsNotNone(r.html.select_one(selector))
#
#    def test_product_view_buttons_only_available_with_proper_perm(self):
#        user = self.create_user()
#        url = reverse("wirgarten:product")
#        r = self.app.get(url, user=user, expect_errors=True)
#        self.assertEqual(r.status_code, 403)
#        user.add_perm(Permission.Products.VIEW)
#        self.assertTrue(user.has_perm(Permission.Products.VIEW))
#        r = self.app.get(url, user=user)
#
#        checks = [
#            (
#                "coop.manage",
#                [
#                    "#growing-period-add-btn",
#                    "#growing-period-copy-form-btn",
#                    "#del-growing-period-btn",
#                ],
#            ),
#            (
#                Permission.Products.MANAGE,
#                [
#                    "#add-capacity-btn",
#                    "#edit-capacity-btn",
#                    "#del-capacity-btn",
#                    "#add-product-btn",
#                    "#edit-product-btn",
#                    "#del-product-btn",
#                ],
#            ),
#        ]
#
#        for perm, selectors in checks:
#            user.add_perm(perm)
#            self.assertTrue(user.has_perm(perm))
#            r = self.app.get(url, user=user)
#            for selector in selectors:
#                self.assertIsNotNone(r.html.select_one(selector), selectors)
