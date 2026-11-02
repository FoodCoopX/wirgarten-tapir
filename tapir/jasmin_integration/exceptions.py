class JasminSynchronisationException(Exception):
    def __init__(self, message: str, *args):
        self.message = message
        super().__init__(message, *args)
