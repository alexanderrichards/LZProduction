"""ParametricJobs Table."""
import re
import json
import logging
from datetime import datetime
from abc import abstractmethod

import cherrypy
from sqlalchemy import Column, Integer, Boolean, String, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from lzproduction.rpc.DiracRPCClient import dirac_api_client, ParametricDiracJobClient, DoNotSubmit
from lzproduction.sql.utils import db_session
from lzproduction.sql.statuses import LOCALSTATUS
from lzproduction.sql.tables.SQLTableBase import SQLTableBase
from lzproduction.sql.tables.JSONTableEncoder import JSONTableEncoder
from lzproduction.sql.tables.DiracJobs import DiracJobs


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
UNIXDATE = re.compile(r'(?P<month>[0-9]{2})-(?P<day>[0-9]{2})-(?P<year>[0-9]{4})$')


@cherrypy.expose
class ParametricJobsBase(SQLTableBase):
    """Jobs SQL Table."""

    __tablename__ = 'parametricjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    site = Column(String(250), nullable=False, default='ANY')
    request_id = Column(Integer, ForeignKey('requests.id'), nullable=False)
    request = relationship("Requests", back_populates="parametricjobs")
    status = Column(Enum(LOCALSTATUS), nullable=False)
    reschedule = Column(Boolean, nullable=False, default=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    num_jobs = Column(Integer, nullable=False)
    num_completed = Column(Integer, nullable=False, default=0)
    num_failed = Column(Integer, nullable=False, default=0)
    num_submitted = Column(Integer, nullable=False, default=0)
    num_running = Column(Integer, nullable=False, default=0)
    diracjobs = relationship("DiracJobs", back_populates="parametricjob")

    @hybrid_property
    def num_other(self):
        """Return the number of jobs in states other than the known ones."""
        return self.num_jobs - (self.num_submitted + self.num_running + self.num_failed + self.num_completed)

    @abstractmethod
    def job_config(self):
        """Configure the DIRAC job."""
#        job = (yield)
        raise NotImplementedError

    def submit(self):
        """Submit parametric job."""
        dirac_ids = set()

        job_coroutine = self.blah()
        job_coroutine.next()
        job_context = ParametricDiracJobClient()
        while True:
            try:
                with job_context as job:
                    try:
                        job_coroutine.send(job)
                        job.setDestination(self.site)
                    except StopIteration:
                        raise DoNotSubmit
                dirac_ids.update(job_context.subjob_ids)
            except DoNotSubmit:
                break

        with db_session() as session:
            session.bulk_insert_mappings(DiracJobs, [{'id': i, 'parametricjob_id': self.id}
                                                     for i in dirac_ids])

    def reset(self):
        """Reset parametric job."""
        with db_session(reraise=False) as session:
            dirac_jobs = session.query(DiracJobs).filter_by(parametricjob_id=self.id)
            dirac_job_ids = [j.id for j in dirac_jobs.all()]
            dirac_jobs.delete(synchronize_session=False)
        with dirac_api_client() as dirac:  # this could be done in diracjobs
            logger.info("Removing Dirac jobs %s from ParametricJob %s", dirac_job_ids, self.id)
            dirac.kill(dirac_job_ids)
            dirac.delete(dirac_job_ids)

    def delete_dirac_jobs(self, session):
        """Delete associated DIRAC jobs."""
        logger.info("Deleting DiracJobs for ParametricJob id: %s", self.id)
        session.query(DiracJobs)\
               .filter_by(parametricjob_id=self.id)\
               .delete(synchronize_session=False)

    def update_status(self):
        """Update the status of parametric job."""
        local_statuses = DiracJobs.update_status(self)
        # could just have DiracJobs return this... maybe better
#        local_statuses = Counter(status.local_status for status in dirac_statuses.elements())
        status = max(local_statuses or [self.status])
        with db_session() as session:
            this = session.merge(self)
            this.status = status
            this.num_completed = local_statuses[LOCALSTATUS.Completed]
            this.num_failed = local_statuses[LOCALSTATUS.Failed]
            this.num_submitted = local_statuses[LOCALSTATUS.Submitted]
            this.num_running = local_statuses[LOCALSTATUS.Running]
            this.reschedule = False
        return status

    @classmethod
    def GET(cls, reqid):  # pylint: disable=invalid-name
        """
        REST Get method.

        Returns all ParametricJobs for a given request id.
        """
        logger.debug("In GET: reqid = %s", reqid)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            user_requests = session.query(cls)\
                                   .filter_by(request_id=reqid)
            if not requester.admin:
                user_requests = user_requests.join(cls.request)\
                                             .filter_by(requester_id=requester.id)
            return json.dumps({'data': user_requests.all()}, cls=JSONTableEncoder)

    @classmethod
    def PUT(cls, jobid, reschedule=False):  # pylint: disable=invalid-name
        """REST Put method."""
        logger.debug("In PUT: jobid = %s, reschedule = %s", jobid, reschedule)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            query = session.query(cls).filter_by(id=jobid)
            if not requester.admin:
                query = query.join(cls.request)\
                             .filter_by(requester_id=requester.id)
            try:
                job = query.one()
            except NoResultFound:
                logger.error("No ParametricJobs found with id: %s", jobid)
            except MultipleResultsFound:
                logger.error("Multiple ParametricJobs found with id: %s", jobid)
            else:
                if reschedule and not job.reschedule:
                    job.reschedule = True
                    job.status = LOCALSTATUS.Submitting
