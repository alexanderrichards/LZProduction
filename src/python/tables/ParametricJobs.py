"""Requests Table."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, PickleType, TIMESTAMP, ForeignKeyConstraint
from sqlalchemy_utils import SQLTableBase


class ParametricJobs(SQLTableBase):
    """Requests SQL Table."""

    __tablename__ = 'parametricjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=C0103
    request_id = Column(Integer, nullable=False)
    status = Column(String(25), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    macro = Column(String(250), nullable=False)
    reduced_lfns = Column(PickleType())
    njobs = Column(Integer, nullable=False)
    nevents = Column(Integer, nullable=False)
    seed = Column(Integer, nullable=False)
    dirac_jobs = Column(PickleType(), nullable=False)
    ForeignKeyConstraint(['request_id'], ['requests.id'])
