"""Dirac Jobs Table."""
from sqlalchemy import Column, Integer, String, ForeignKey
from .SQLTableBase import SQLTableBase


class DiracJobs(SQLTableBase):
    """Dirac Jobs SQL Table."""

    __tablename__ = 'diracjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    parametricjob_id = Column(Integer, ForeignKey('parametricjobs.id'), nullable=False)
    name = Column(String(30))
    status = Column(String(14), nullable=False)
    reschedules = Column(Integer, nullable=False, default=0)
