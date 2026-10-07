class EmailNormaliser:
    @staticmethod
    def normalise(email_address: str):
        return email_address.strip().lower()
