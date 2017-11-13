"""Services Table."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP, Enum
from .SQLTableBase import SQLTableBase
from ..statuses import SERVICESTATUS


class Services(SQLTableBase):
    """Services SQL Table."""

    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    name = Column(String(25), nullable=False)
    status = Column(Enum(SERVICESTATUS), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
