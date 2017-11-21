"""Users Table."""
from sqlalchemy import Column, Integer, String, Boolean
from .SQLTableBase import SQLTableBase


class Users(SQLTableBase):
    """Users SQL Table."""

    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    dn = Column(String(250), nullable=False)  # pylint: disable=invalid-name
    ca = Column(String(250), nullable=False)  # pylint: disable=invalid-name
    email = Column(String(250), nullable=False)
    suspended = Column(Boolean, nullable=False)
    admin = Column(Boolean, nullable=False)

    @property
    def name(self):
        """
        Human-readable name from DN.

        Attempt to determine a meaningful name from a
        clients DN. Requires the DN to have already been
        converted to the more usual slash delimeted style.
        If multiple CN fields exist in the DN then the longest
        is assumend to be the desired human readable field.

        Returns:
            str: The human-readable name
        """
        cns = (token[len('CN='):] for token in self.dn.split('/')
               if token.startswith('CN='))
        return sorted(cns, key=len)[-1]

    def __hash__(self):
        return hash((self.dn, self.ca))

    def __eq__(self, other):
        return (self.dn, self.ca) == (other.dn, other.ca)
