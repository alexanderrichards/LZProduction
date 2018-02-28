"""ParametricJobs Table."""
import os
import re
import time
import json
import logging
import calendar
from abc import abstractmethod
from datetime import datetime
from copy import deepcopy
from collections import defaultdict, Counter

import cherrypy
from sqlalchemy import Column, SmallInteger, Integer, Boolean, String, PickleType, TIMESTAMP, ForeignKey, Enum, CheckConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from lzproduction.rpc.DiracRPCClient import dirac_api_client, ParametricDiracJobClient
from lzproduction.utils.collections import list_splitter
from lzproduction.utils.tempfile_utils import temporary_runscript, temporary_macro
from ..utils import db_session
from ..statuses import LOCALSTATUS, DIRACSTATUS
from .SQLTableBase import SQLTableBase
from .JSONTableEncoder import JSONTableEncoder
from .DiracJobs import DiracJobs


UNIXDATE = re.compile(r'(?P<month>[0-9]{2})-(?P<day>[0-9]{2})-(?P<year>[0-9]{4})$')


@cherrypy.expose
class ParametricJobsBase(SQLTableBase):
    """Jobs SQL Table."""

    __tablename__ = 'parametricjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    priority = Column(SmallInteger, CheckConstraint('priority >= 0 and priority < 10'), nullable=False, default=3)
    site = Column(String(250), nullable=False, default='ANY')
    request_id = Column(Integer, ForeignKey('requests.id'), nullable=False)
    request = relationship("Requests", back_populates="parametricjobs")
    status = Column(Enum(LOCALSTATUS), nullable=False, default=LOCALSTATUS.Requested)
    reschedule = Column(Boolean, nullable=False, default=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    num_jobs = Column(Integer, nullable=False)
    num_completed = Column(Integer, nullable=False, default=0)
    num_failed = Column(Integer, nullable=False, default=0)
    num_submitted = Column(Integer, nullable=False, default=0)
    num_running = Column(Integer, nullable=False, default=0)
    diracjobs = relationship("DiracJobs", back_populates="parametricjob", cascade="all, delete-orphan")
    logger = logging.getLogger(__name__)

    @hybrid_property
    def num_other(self):
        """Return the number of jobs in states other than the known ones."""
        return self.num_jobs - (self.num_submitted + self.num_running + self.num_failed + self.num_completed)

    @abstractmethod
    def _create_dirac_jobs(self):
        """Create the DIRAC jobs."""
        parametric_job = ParametricDiracJobClient()
        with parametric_job as job:
            job.setName('test')
        return parametric_job.subjob_ids

    def submit(self):
        """Submit parametric job."""
        self.status = LOCALSTATUS.Submitting
        dirac_ids = self._create_dirac_jobs()
#        if not isinstance(dirac_ids, Iterable):
#            raise Exception
        self.diracjobs = [DiracJobs(id=dirac_id, parametricjob_id=self.id)
                          for dirac_id in dirac_ids]

    def reset(self):
        """Reset parametric job."""
        dirac_job_ids = set(job.id for job in self.diracjobs)
#        DiracJobs.delete_all(self)
        self.diracjobs = []
        with dirac_api_client() as dirac:
            self.logger.info("Removing Dirac jobs %s from ParametricJob %s", dirac_job_ids, self.id)
            dirac.kill(dirac_job_ids)
            dirac.delete(dirac_job_ids)


    def update_status(self):
        """Update the status of parametric job."""
        if not self.diracjobs:
            self.logger.warning("No dirac jobs associated with parametricjob: %s. "
                                "returning status unknown", self.id)
            self.status = LOCALSTATUS.Unknown
            self.num_completed = 0
            self.num_failed = 0
            self.num_submitted = 0
            self.num_running = 0
            self.reschedule = False
            return self.status

        # Group jobs by status
        job_types = defaultdict(set)
        for job in self.diracjobs:
            job_types[job.status].add(job.id)
            # add auto-reschedule jobs
            if job.status in (DIRACSTATUS.Failed, DIRACSTATUS.Stalled) and job.reschedules < 2:
                job_types['Reschedule'].add(job.id)

        reschedule_jobs = job_types['Reschedule'] if job_types[DIRACSTATUS.Done] else set()
        monitor_jobs = job_types[DIRACSTATUS.Running] | \
                       job_types[DIRACSTATUS.Received] | \
                       job_types[DIRACSTATUS.Queued] | \
                       job_types[DIRACSTATUS.Waiting] | \
                       job_types[DIRACSTATUS.Checking] | \
                       job_types[DIRACSTATUS.Matched] | \
                       job_types[DIRACSTATUS.Unknown] | \
                       job_types[DIRACSTATUS.Completed]

        if self.reschedule:
            reschedule_jobs = job_types[DIRACSTATUS.Failed] | job_types[DIRACSTATUS.Stalled]

        # Reschedule jobs
        rescheduled_jobs = ()
        if reschedule_jobs:
            with dirac_api_client() as dirac:
                result = deepcopy(dirac.reschedule(reschedule_jobs))
            if result['OK']:
                rescheduled_jobs = result['Value']
                self.logger.info("Rescheduled jobs: %s", rescheduled_jobs)
                monitor_jobs.update(rescheduled_jobs)
                skipped_jobs = reschedule_jobs.difference(rescheduled_jobs)
                if skipped_jobs:
                    self.logger.warning("Failed to reschedule jobs: %s", list(skipped_jobs))
            else:
                self.logger.error("Problem rescheduling jobs: %s", result['Message'])

        # Monitor jobs statuses
        with dirac_api_client() as dirac:
            result = deepcopy(dirac.status(monitor_jobs))
        if not result['OK']:
            raise Exception(result['Message'])
        monitored_jobs = result['Value']
        skipped_jobs = monitor_jobs.difference(monitored_jobs)
        if skipped_jobs:
            self.logger.warning("Couldn't check the status of jobs: %s", list(skipped_jobs))

        # Update database
        local_statuses = Counter()
        for job in self.diracjobs:
            if job.id in rescheduled_jobs:
                job.reschedules += 1
            if job.id in monitored_jobs:
                job.status = DIRACSTATUS[monitored_jobs[job.id]['Status']]
            local_statuses.update((job.status.local_status,))

        self.status = max(local_statuses or [self.status])
        self.num_completed = local_statuses[LOCALSTATUS.Completed]
        self.num_failed = local_statuses[LOCALSTATUS.Failed]
        self.num_submitted = local_statuses[LOCALSTATUS.Submitted]
        self.num_running = local_statuses[LOCALSTATUS.Running]
        self.reschedule = False
        return self.status


    @classmethod
    def GET(cls, reqid):  # pylint: disable=invalid-name
        """
        REST Get method.

        Returns all ParametricJobs for a given request id.
        """
        cls.logger.debug("In GET: reqid = %s", reqid)
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
        cls.logger.debug("In PUT: jobid = %s, reschedule = %s", jobid, reschedule)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            query = session.query(cls).filter_by(id=jobid)
            if not requester.admin:
                query = query.join(cls.request)\
                             .filter_by(requester_id=requester.id)
            try:
                job = query.one()
            except NoResultFound:
                cls.logger.error("No ParametricJobs found with id: %s", jobid)
            except MultipleResultsFound:
                cls.logger.error("Multiple ParametricJobs found with id: %s", jobid)
            else:
                if reschedule and not job.reschedule:
                    job.reschedule = True
                    job.status = LOCALSTATUS.Submitting

