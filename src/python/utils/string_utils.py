"""String Utilities."""
import string


class DefaultFormatter(string.Formatter):
    """
    String formatter with default value.

    Performs normal string formatting except when there is a missing key
    the default value is used.
    """

    def __init__(self, missing):
        """
        Initialise.

        Args:
            missing (any): The default value to insert, must have a
                           string representation.
        """
        self._missing = str(missing)

    def get_field(self, field_name, args, kwargs):
        """
        Get field.

        Returns the value of the given field returning the default
        value if no such field exists. This method should not be called
        by the user directly, it is invoked by the inherited format method.
        """
        try:
            return super(DefaultFormatter, self).get_field(field_name, args, kwargs)
        except (IndexError, KeyError):
            return self._missing, field_name
