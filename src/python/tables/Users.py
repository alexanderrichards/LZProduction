"""Users Table."""
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy_utils import SQLTableBase

class Users(SQLTableBase):
    """Users SQL Table."""

    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    dn = Column(String(250), nullable=False)
    ca = Column(String(250), nullable=False)
    suspended = Column(Boolean(), nullable=False)
    admin = Column(Boolean(), nullable=False)
