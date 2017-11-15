"""Dirac Jobs Table."""
import logging
from copy import deepcopy
from collections import Counter, defaultdict

from sqlalchemy import Column, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship

from rpc.DiracRPCClient import dirac_api_client
from ..utils import db_session
from ..statuses import DIRACSTATUS
from .SQLTableBase import SQLTableBase


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class DiracJobs(SQLTableBase):
    """Dirac Jobs SQL Table."""

    __tablename__ = 'diracjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    parametricjob_id = Column(Integer, ForeignKey('parametricjobs.id'), nullable=False)
    parametricjob = relationship("ParametricJobs", back_populates='diracjobs')
    status = Column(Enum(DIRACSTATUS), nullable=False, default=DIRACSTATUS.Unknown)
    reschedules = Column(Integer, nullable=False, default=0)

    @staticmethod
    def update_status(parametricjob):
        """
        Bulk update status.

        This method updates all DIRAC jobs which belong to the given
        parametricjob.
        """
        with db_session() as session:
            dirac_jobs = session.query(DiracJobs)\
                                .filter_by(parametricjob_id=parametricjob.id)\
                                .all()
            session.expunge_all()

        # Group jobs by status
        job_types = defaultdict(set)
        for job in dirac_jobs:
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

        if parametricjob.reschedule:
            reschedule_jobs = job_types[DIRACSTATUS.Failed] | job_types[DIRACSTATUS.Stalled]

        # Reschedule jobs
        if reschedule_jobs:
            with dirac_api_client() as dirac:
                result = deepcopy(dirac.reschedule(reschedule_jobs))
            if result['OK']:
                logger.info("Rescheduled jobs: %s", result['Value'])
                monitor_jobs.update(result['Value'])
                with db_session(reraise=False) as session:
                    session.query(DiracJobs)\
                           .filter(DiracJobs.id.in_(result['Value']))\
                           .update({'reschedules': DiracJobs.reschedules + 1},
                                   synchronize_session=False)
#                    rescheduled_jobs = session.query(DiracJobs.id, DiracJobs.reschedules)\
#                                              .filter(DiracJobs.id.in_(results['Value']))\
#                                              .all()
#                    session.bulk_update_mappings(DiracJobs, [dict(job._asdict(), reschedules=job.reschedules + 1)
#                                                             for job in rescheduled_jobs])
                skipped_jobs = reschedule_jobs.difference(result["Value"])
                if skipped_jobs:
                    logger.warning("Failed to reschedule jobs: %s", list(skipped_jobs))
            else:
                logger.error("Problem rescheduling jobs: %s", result['Message'])

        # Update status
        with dirac_api_client() as dirac:
            dirac_answer = deepcopy(dirac.status(monitor_jobs))
        if not dirac_answer['OK']:
            raise DiracError(dirac_answer['Message'])
        dirac_statuses = dirac_answer['Value']

        skipped_jobs = monitor_jobs.difference(dirac_statuses)
        if skipped_jobs:
            logger.warning("Couldn't check the status of jobs: %s", list(skipped_jobs))

        with db_session() as session:
#            session.query(DiracJobs)\
#                   .filter(DiracJobs.id.in_(dirac_statuses.keys()))\
#                   .update({'status': DIRACSTATUS[dirac_statuses[DiracJobs.id]['Status']]})
            session.bulk_update_mappings(DiracJobs, [{'id': i, 'status': DIRACSTATUS[j['Status']]}
                                                      for i, j in dirac_statuses.iteritems()])
            session.flush()
            session.expire_all()
            dirac_jobs = session.query(DiracJobs)\
                                .filter_by(parametricjob_id=parametricjob.id)\
                                .all()
            session.expunge_all()

        if not dirac_jobs:
            logger.warning("No dirac jobs associated with parametricjob: %s. returning status unknown", parametricjob.id)
            return Counter([DIRACSTATUS.Unknown.local_status])
        return Counter(job.status.local_status for job in dirac_jobs)
