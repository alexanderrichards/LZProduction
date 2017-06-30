"""Requests Table."""
import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP, Text, PickleType, ForeignKeyConstraint
from sqlalchemy_utils import SQLTableBase, nonexpiring, continuing
from tables import ParametricJobs
from utils.coroutine_utils import status_accumulator

logger = logging.getLogger(__name__)

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
        self.status = "Submitting"
        with nonexpiring(scoped_session) as session:
            jobs = session.query(ParametricJobs).filter(ParametricJobs.request_id == self.id).all()
            this = session.query(Requests).filter(Requests.id == self.id).first()
            if this is not None:
                this.status = self.status
                logger.info("Request %s moved to state %s", self.id, self.status)

        status_acc = status_accumulator(('Unknown', 'Deleted', 'Killed', 'Completed', 'Failed', 'Requested', 'Approved', 'Submitted', 'Submitting', 'Running'))

        try:
            logger.info("Submitting request %s", self.id)
            for i, job in enumerate(jobs):
                self.status = status_acc.send(job.submit(scoped_session))
        except:
            logger.exception("Exception while submitting request %s", self.id)
            logger.info("Resetting associated ParametricJobs")
            for j in jobs[:i]:
                j.reset()
        else:
            with continuing(scoped_session) as session:
                this = session.query(Requests).filter(Requests.id == self.id).first()
                if this is not None:
                    this.status = self.status
                    logger.info("Request %s moved to state %s", self.id, self.status)


    def update_status(self, scoped_session):
        status_acc = status_accumulator(('Unknown', 'Deleted', 'Killed', 'Completed', 'Failed', 'Requested', 'Approved', 'Submitted', 'Submitting', 'Running'))
        # with sqlalchemy_utils.db_session(self.dburl) as session:
        with nonexpiring(scoped_session) as session:
            jobs = session.query(ParametricJobs).filter(ParametricJobs.request_id == self.id).all()

        update = True
        init_status = self.status
        for job in jobs:
            try:
                # with sqlalchemy_utils.db_subsession(session):
                self.status = status_acc.send(job.update_status(scoped_session))
            except:
                logger.exception("Exception updating ParametricJob %s", job.id)
                update = False

        if update and self.status != init_status:
            with continuing(scoped_session) as session:
                this = session.query(Requests).filter(Requests.id == self.id).first()
                if this is not None:
                    this.status = self.status
                    logger.info("Request %s moved to state %s", self.id, self.status)
