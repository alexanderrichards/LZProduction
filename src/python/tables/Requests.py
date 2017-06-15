"""Requests Table."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP, Text, PickleType, ForeignKeyConstraint
from sqlalchemy_utils import SQLTableBase, nonexpiring, continuing
from tables import ParametricJobs
from coroutine_utils import status_accumulator

class Requests(SQLTableBase):
    """Requests SQL Table."""

    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)  # pylint: disable=C0103
    requester_id = Column(Integer, nullable=False)
    request_date = Column(String(250), nullable=False)
    source = Column(String(250), nullable=False)
    detector = Column(String(250), nullable=False)
    sim_lead = Column(String(250), nullable=False)
    status = Column(String(250), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(String(250), nullable=False)
    ForeignKeyConstraint(['requester_id'], ['users.id'])


    def submit(self, scoped_session):
        status_acc = status_accumulator(('Unknown', 'Deleted', 'Killed', 'Completed', 'Failed', 'Requested', 'Approved', 'Submitted', 'Running'))
        # with sqlalchemy_utils.db_session(self.dburl) as session:
        with nonexpiring(scoped_session) as session:
            jobs = session.query(ParametricJobs).filter(ParametricJobs.request_id == self.id).all()

        for job in jobs:
            # with sqlalchemy_utils.db_subsession(session):
            self.status = status_acc.send(job.submit())

        with continuing(scoped_session) as session:
            for job in jobs:
                session.merge(job)

    def update_status(self, scoped_session):
        status_acc = status_accumulator(('Unknown', 'Deleted', 'Killed', 'Completed', 'Failed', 'Requested', 'Approved', 'Submitted', 'Running'))
        # with sqlalchemy_utils.db_session(self.dburl) as session:
        with nonexpiring(scoped_session) as session:
            jobs = session.query(ParametricJobs).filter(ParametricJobs.request_id == self.id).all()

        for job in jobs:
            # with sqlalchemy_utils.db_subsession(session):
            self.status = status_acc.send(job.update_status())

        with continuing(scoped_session) as session:
            for job in jobs:
                session.merge(job)
