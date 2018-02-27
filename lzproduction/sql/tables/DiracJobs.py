"""Dirac Jobs Table."""
from sqlalchemy import Column, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship

from ..statuses import DIRACSTATUS
from .SQLTableBase import SQLTableBase


class DiracJobs(SQLTableBase):
    """Dirac Jobs SQL Table."""

    __tablename__ = 'diracjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    parametricjob_id = Column(Integer, ForeignKey('parametricjobs.id'), nullable=False)
    parametricjob = relationship("ParametricJobs", back_populates='diracjobs')
    status = Column(Enum(DIRACSTATUS), nullable=False, default=DIRACSTATUS.Unknown)
    reschedules = Column(Integer, nullable=False, default=0)
