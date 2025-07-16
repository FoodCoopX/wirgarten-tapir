from tapir.log.models import LogEntry


class WaitingListChangeConfirmedLogEntry(LogEntry):
    """
    This log entry is created whenever a user uses a confirmation link they received per mail, coming from a waiting list entry
    """

    template_name = "waiting_list/log/waiting_list_change_confirmed_log_entry.html"
