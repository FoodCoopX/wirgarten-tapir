import datetime

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberExtraEmailApiViewGet(TapirIntegrationTest):
    maxDiff = 3000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=True)

    def test_get_featureIsDisabled_returns400(self):
        self.client.force_login(MemberFactory.create())
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=False)

        response = self.client.get(reverse("core:member_extra_emails"))

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_get_default_returnsCorrectData(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        now = timezone.now()
        confirmed = MemberExtraEmail.objects.create(
            email="confirmed@example.com",
            member=member,
            confirmed_on=now,
        )
        unconfirmed = MemberExtraEmail.objects.create(
            email="unconfirmed@example.com", member=member, confirmed_on=None
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.EXPLANATION_TEXT_EXTRA_MAIL_ADDRESSES
        ).update(value="test text")

        url = reverse("core:member_extra_emails")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        # depending on the testing machines locale, the "confirmed_on" field may be serialized with a different timezone
        # so we first check the equality of the deserialized datetime.
        actual_datetime = datetime.datetime.fromisoformat(
            response_content["extra_mails"][0]["confirmed_on"]
        )
        self.assertEqual(now, actual_datetime)

        self.assertEqual(
            {
                "extra_mails": [
                    {
                        "id": confirmed.id,
                        "member": member.id,
                        "email": "confirmed@example.com",
                        "confirmed_on": response_content["extra_mails"][0][
                            "confirmed_on"
                        ],
                        "secret": str(confirmed.secret),
                    },
                    {
                        "id": unconfirmed.id,
                        "member": member.id,
                        "email": "unconfirmed@example.com",
                        "confirmed_on": None,
                        "secret": str(unconfirmed.secret),
                    },
                ],
                "explanation_text": "test text",
            },
            response_content,
        )

    def test_get_adminGetsDataFromAnotherMember_returns200(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        other_member = MemberFactory.create()

        url = reverse("core:member_extra_emails")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_normalMemberGetsDataFromAnotherMember_returns403(self):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        other_member = MemberFactory.create()

        url = reverse("core:member_extra_emails")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
