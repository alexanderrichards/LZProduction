"""Users Table."""
from sqlalchemy import Column, Integer, String, Boolean
from utils.sqlalchemy_utils import SQLTableBase


class Users(SQLTableBase):
    """Users SQL Table."""

    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)  # pylint: disable=C0103
    dn = Column(String(250), nullable=False)  # pylint: disable=C0103
    ca = Column(String(250), nullable=False)  # pylint: disable=C0103
    email = Column(String(250), nullable=False)
    suspended = Column(Boolean(), nullable=False)
    admin = Column(Boolean(), nullable=False)

    def __hash__(self):
        return hash((self.dn, self.ca))

    def __eq__(self, other):
        return (self.dn, self.ca) == (other.dn, other.ca)
