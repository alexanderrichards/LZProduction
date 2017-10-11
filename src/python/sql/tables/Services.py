"""Services Table."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP
from .SQLTableBase import SQLTableBase


class Services(SQLTableBase):
    """Services SQL Table."""

    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)  # pylint: disable=C0103
    name = Column(String(25), nullable=False)
    status = Column(String(10), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
