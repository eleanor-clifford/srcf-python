from srcf import pwgen


class Password:
    """
    Container of randomly generated passwords.

    Attributes:
        value (str):
            Plaintext password.
    """

    def __init__(self, value):
        self.value = value

    @classmethod
    def new(cls):
        """
        Generate a fresh new password.

        Returns:
            .Password
        """
        return cls(pwgen().decode("utf-8"))
