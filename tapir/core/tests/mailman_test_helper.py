import unittest
from dataclasses import dataclass, field
from unittest.mock import patch, Mock

from django.conf import settings

from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient


@dataclass
class MockMailingListData:
    name: str
    confirmed_recipients: list[str] = field(default_factory=list)
    unconfirmed_recipients: list[str] = field(default_factory=list)


class MailmanTestHelper:
    @classmethod
    def mock_domain(
        cls, test: unittest.TestCase, mailing_list_datas: list[MockMailingListData]
    ):
        if not hasattr(test, "mock_client"):
            patcher_client = patch.object(TapirMailmanClient, "get_client")
            test.mock_get_client = patcher_client.start()
            test.addCleanup(patcher_client.stop)

        client = Mock()
        test.mock_get_client.return_value = client
        domain = Mock()
        client.get_domain.return_value = domain
        domain.lists = [
            cls.build_mock_list(mailing_list) for mailing_list in mailing_list_datas
        ]
        domain.create_list.side_effect = lambda list_name: cls.build_mock_list(
            MockMailingListData(
                name=list_name, unconfirmed_recipients=[], confirmed_recipients=[]
            )
        )
        return domain

    @classmethod
    def build_mock_list(cls, mailing_list_data: MockMailingListData):
        mock_list = Mock()
        mock_list.fqdn_listname = f"{mailing_list_data.name}@{settings.EMAIL_HOST}"
        mock_list.members = [
            Mock(address=recipient)
            for recipient in mailing_list_data.confirmed_recipients
        ]
        mock_list.requests = [
            {"email": recipient}
            for recipient in mailing_list_data.unconfirmed_recipients
        ]
        return mock_list
