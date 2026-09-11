class TapirDataImportException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class DryRunException(Exception):
    pass
