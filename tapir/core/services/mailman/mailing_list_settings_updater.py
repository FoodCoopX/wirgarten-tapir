from mailmanclient import MailingList


class MailingListSettingsUpdater:
    MODERATED_MEMBER_ACTION = "hold"
    UNMODERATED_MEMBER_ACTION = "defer"

    @classmethod
    def update_settings(
        cls,
        mailing_list: MailingList,
        advertised: bool,
        description: str,
        moderated: bool,
    ):
        mailing_list.settings["advertised"] = advertised
        mailing_list.settings["description"] = description
        mailing_list.settings["default_member_action"] = (
            cls.MODERATED_MEMBER_ACTION if moderated else cls.UNMODERATED_MEMBER_ACTION
        )
        mailing_list.settings["preferred_language"] = "de"
        mailing_list.settings.save()

    @classmethod
    def is_moderated(cls, mailing_list: MailingList) -> bool:
        return (
            mailing_list.settings["default_member_action"]
            == cls.MODERATED_MEMBER_ACTION
        )
