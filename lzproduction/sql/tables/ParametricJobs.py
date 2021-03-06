"""ParametricJobs Table."""
import os
import re
import time
import json
import logging
import calendar
from datetime import datetime

import cherrypy
from sqlalchemy import Column, SmallInteger, Integer, Boolean, String, PickleType, TIMESTAMP, ForeignKey, Enum, CheckConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from lzproduction.rpc.DiracRPCClient import dirac_api_client, ParametricDiracJobClient
from lzproduction.utils.collections import list_splitter
from lzproduction.utils.tempfile_utils import temporary_runscript, temporary_macro
from ..utils import db_session
from ..statuses import LOCALSTATUS
from .SQLTableBase import SQLTableBase
from .JSONTableEncoder import JSONTableEncoder
from .DiracJobs import DiracJobs


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
UNIXDATE = re.compile(r'(?P<month>[0-9]{2})-(?P<day>[0-9]{2})-(?P<year>[0-9]{4})$')


@cherrypy.expose
class ParametricJobs(SQLTableBase):
    """Jobs SQL Table."""

    __tablename__ = 'parametricjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    priority = Column(SmallInteger, CheckConstraint('priority >= 0 and priority < 10'), nullable=False, default=3)
    app = Column(String(250))
    app_version = Column(String(250))
    site = Column(String(250), nullable=False, default='ANY')
    sim_lfn_outputdir = Column(String(250))
    mctruth_lfn_outputdir = Column(String(250))
    macro = Column(String(250))
    tag = Column(String(250))
    njobs = Column(Integer)
    nevents = Column(Integer)
    seed = Column(Integer)
    hour = Column(Integer)
    fastnest_version = Column(String(250))
    reduction_version = Column(String(250))
    reduction_lfn_inputdir = Column(String(250))
    reduction_lfn_outputdir = Column(String(250))
    der_version = Column(String(250))
    der_lfn_inputdir = Column(String(250))
    der_lfn_outputdir = Column(String(250))
    lzap_version = Column(String(250))
    physics_version = Column(String(250))
    lzap_lfn_inputdir = Column(String(250))
    lzap_lfn_outputdir = Column(String(250))
    request_id = Column(Integer, ForeignKey('requests.id'), nullable=False)
    request = relationship("Requests", back_populates="parametricjobs")
    status = Column(Enum(LOCALSTATUS), nullable=False)
    reschedule = Column(Boolean, nullable=False, default=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    num_completed = Column(Integer, nullable=False, default=0)
    num_failed = Column(Integer, nullable=False, default=0)
    num_submitted = Column(Integer, nullable=False, default=0)
    num_running = Column(Integer, nullable=False, default=0)
    diracjobs = relationship("DiracJobs", back_populates="parametricjob")

    @hybrid_property
    def num_other(self):
        """Return the number of jobs in states other than the known ones."""
        return self.njobs - (self.num_submitted + self.num_running + self.num_failed + self.num_completed)

    def submit(self):
        """Submit parametric job."""
        # problems here if not running simulation, there will be no macro so
        # everything including context needs reworking.
#        lfn_root = os.path.join('/lz/user/l/lzproduser.grid.hep.ph.ic.ac.uk', '_'.join(('-'.join((self.app, self.app_version)),
#                                                           '-'.join(('DER', self.der_version)))))

        parametric_job = ParametricDiracJobClient()
        dirac_ids = set()
        if self.app_version is not None:

            macro_name = os.path.splitext(os.path.basename(self.macro or ''))[0]
            livetime_sec_per_beamon = 0.1132698957
            livetimeperjob = str((self.nevents or 1) * livetime_sec_per_beamon)
            unixtime = time.time()
            match = UNIXDATE.search(macro_name)
            if match is not None:
                month, day, year = match.groups()
                unixtime = str(int(calendar.timegm(datetime(int(year), int(month), int(day), 0, 0).utctimetuple())))
            with temporary_runscript(root_version='5.34.32',
                                     root_arch='slc6_gcc44_x86_64',
                                     g4_version='4.10.03.p02',
                                     se='UKI-LT2-IC-HEP-disk',
                                     unixtime=unixtime,
                                     livetimeperjob=livetimeperjob, **self) as runscript,\
                 temporary_macro(self.tag, self.macro or '', self.app, self.app_version, self.nevents) as macro:
                logger.info("Submitting ParametricJob %s, macro: %s to DIRAC", self.id, self.macro)
                for sublist in list_splitter(range(self.seed, self.seed + self.njobs), 1000):
                    with parametric_job as j:
                        j.setName(os.path.splitext(os.path.basename(macro))[0] + '-%(args)s')
                        j.setPriority(self.priority)
                        j.setPlatform('ANY')
                        j.setExecutable(os.path.basename(runscript),
                                        os.path.basename(macro) + ' %(args)s' + ' %s' % self.nevents,
                                        'lzproduction_output.log')
                        j.setInputSandbox([runscript, macro])
                        if self.site.endswith('2Processors'):
                            j.setDestination("LCG.UKI-LT2-IC-HEP.uk")  # this should be done with site, tag = self.site.split(' ')
                            j.setTag('2Processors')
                        elif self.site.endswith("HighMem"):
                            j.setDestination("LCG.UKI-SOUTHGRID-RALPP.uk")
                            j.setTag('HighMem')
                        else:
                            j.setDestination(self.site)
                        j.setBannedSites(['LCG.UKI-LT2-Brunel.uk',
                                          'LCG.UKI-NORTHGRID-LANCS-HEP.uk',
                                          'LCG.UKI-SOUTHGRID-BRIS-HEP.uk',
                                          'VAC.UKI-NORTHGRID-MAN-HEP.uk',
                                          'VAC.UKI-NORTHGRID-LANCS-HEP.uk',
                                          'VAC.UKI-NORTHGRID-LIV-HEP.uk',
                                          'VAC.UKI-SOUTHGRID-BHAM-HEP.uk',
                                          'VAC.UKI-SOUTHGRID-CAM-HEP.uk',
                                          'VAC.UKI-SOUTHGRID-OX-HEP.uk',
                                          'VAC.UKI-SCOTGRID-GLASGOW.uk',
                                          'VAC.UKI-LT2-RHUL.uk',
                                          'VAC.UKI-LT2-UCL-HEP.uk'])
                        j.setParameterSequence('args', sublist, addToWorkflow=False)
                    dirac_ids.update(parametric_job.subjob_ids)
        else:
            with temporary_runscript(root_version='5.34.32',
                                     root_arch='slc6_gcc44_x86_64',
                                     g4_version='4.10.03.p02',
                                     se='UKI-LT2-IC-HEP-disk', **self) as runscript:
                logger.info("Submitting ParametricJob %s, inputdir: %s to DIRAC", self.id, self.reduction_lfn_inputdir or self.der_lfn_inputdir or self.lzap_lfn_inputdir)

                input_lfn_dir=self.reduction_lfn_inputdir or\
                               self.der_lfn_inputdir or \
                               self.lzap_lfn_inputdir
                with parametric_job as j:
                    j.setName(input_lfn_dir + "_%(hour)s")
                    j.setPriority(self.priority)
                    j.setPlatform('ANY')
                    j.setExecutable(os.path.basename(runscript),
                                    input_lfn_dir + " %(hour)s",
                                    'lzanalysis_output.log')
                    j.setInputSandbox([runscript])
                    if self.site.endswith('2Processors'):
                        j.setDestination("LCG.UKI-LT2-IC-HEP.uk")
                        j.setTag('2Processors')
                    elif self.site.endswith("HighMem"):
                        j.setDestination("LCG.UKI-SOUTHGRID-RALPP.uk")
                        j.setTag('HighMem')
                    else:
                        j.setDestination(self.site)
                    j.setBannedSites(['LCG.UKI-LT2-Brunel.uk',
                                      'LCG.UKI-NORTHGRID-LANCS-HEP.uk',
                                      'LCG.UKI-SOUTHGRID-BRIS-HEP.uk',
                                      'VAC.UKI-NORTHGRID-MAN-HEP.uk',
                                      'VAC.UKI-NORTHGRID-LANCS-HEP.uk',
                                      'VAC.UKI-NORTHGRID-LIV-HEP.uk',
                                      'VAC.UKI-SOUTHGRID-BHAM-HEP.uk',
                                      'VAC.UKI-SOUTHGRID-CAM-HEP.uk',
                                      'VAC.UKI-SOUTHGRID-OX-HEP.uk',
                                      'VAC.UKI-SCOTGRID-GLASGOW.uk',
                                      'VAC.UKI-LT2-RHUL.uk',
                                      'VAC.UKI-LT2-UCL-HEP.uk'])
                    j.setParameterSequence('hour', self.hour.split(','), addToWorkflow=False)

                dirac_ids.update(parametric_job.subjob_ids)

        with db_session() as session:
            session.bulk_insert_mappings(DiracJobs, [{'id': i, 'parametricjob_id': self.id}
                                                     for i in dirac_ids])

    def reset(self):
        """Reset parametric job."""
        with db_session(reraise=False) as session:
            dirac_jobs = session.query(DiracJobs).filter_by(parametricjob_id=self.id)
            dirac_job_ids = [j.id for j in dirac_jobs.all()]
            dirac_jobs.delete(synchronize_session=False)
        with dirac_api_client() as dirac:
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


    @staticmethod
    def GET(reqid):  # pylint: disable=invalid-name
        """
        REST Get method.

        Returns all ParametricJobs for a given request id.
        """
        logger.debug("In GET: reqid = %s", reqid)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            user_requests = session.query(ParametricJobs)\
                                   .filter_by(request_id=reqid)
            if not requester.admin:
                user_requests = user_requests.join(ParametricJobs.request)\
                                             .filter_by(requester_id=requester.id)
            return json.dumps({'data': user_requests.all()}, cls=JSONTableEncoder)

    @staticmethod
    def PUT(jobid, reschedule=False):  # pylint: disable=invalid-name
        """REST Put method."""
        logger.debug("In PUT: jobid = %s, reschedule = %s", jobid, reschedule)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            query = session.query(ParametricJobs).filter_by(id=jobid)
            if not requester.admin:
                query = query.join(ParametricJobs.request)\
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

