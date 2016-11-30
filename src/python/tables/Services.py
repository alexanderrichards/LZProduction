"""Services Table."""
from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy_utils import SQLTableBase

class Services(SQLTableBase):
    """Services SQL Table."""

    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)
    name = Column(String(25), nullable=False)
    status = Column(String(10), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
