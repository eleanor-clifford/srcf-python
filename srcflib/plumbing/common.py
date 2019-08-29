from srcf import pwgen


class Password:
    """
    Container of randomly generated passwords.  Use ``str(passwd)`` to get the actual value.
    """

    def __init__(self, value, template="{}"):
        self._value = value
        self._template = template

    def __str__(self):
        return self._template.format(self._value)

    def __repr__(self):
        return "<{}: {!r}>".format(self.__class__.__name__, self._template.format("***"))

    @classmethod
    def new(cls):
        """
        Generate a fresh new password.

        Returns:
            .Password
        """
        return cls(pwgen().decode("utf-8"))
