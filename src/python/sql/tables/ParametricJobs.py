"""ParametricJobs Table."""
import os
import logging
import time
import calendar
import re
from datetime import datetime
from sqlalchemy import Column, Integer, Boolean, String, PickleType, TIMESTAMP, ForeignKey, Enum
from .SQLTableBase import SQLTableBase
from ..utils import db_session
from ..statuses import LOCALSTATUS
from rpc.DiracRPCClient import dirac_api_client, ParametricDiracJobClient
from utils.tempfile_utils import temporary_runscript, temporary_macro

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
UNIXDATE = re.compile(r'(?P<month>[0-9]{2})-(?P<day>[0-9]{2})-(?P<year>[0-9]{4})$')

def list_splitter(sequence, nentries):
    """Split sequence into groups."""
    # iterable must be of type Sequence
    for i in xrange(0, len(sequence), nentries):
        yield sequence[i:i + nentries]

class ParametricJobs(SQLTableBase):
    """Jobs SQL Table."""

    __tablename__ = 'parametricjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    app = Column(String(250))
    app_version = Column(String(250))
    sim_lfn_outputdir = Column(String(250))
    mctruth_lfn_outputdir = Column(String(250))
    macro = Column(String(250))
    tag = Column(String(250))
    njobs = Column(Integer)
    nevents = Column(Integer)
    seed = Column(Integer)
    fastnest_version = Column(String(250))
    reduction_version = Column(String(250))
    reduction_lfn_inputdir = Column(String(250))
    reduction_lfn_outputdir = Column(String(250))
    der_version = Column(String(250))
    der_lfn_inputdir = Column(String(250))
    der_lfn_outputdir = Column(String(250))
    lzap_version = Column(String(250))
    lzap_lfn_inputdir = Column(String(250))
    lzap_lfn_outputdir = Column(String(250))
    request_id = Column(Integer, ForeignKey('requests.id'), nullable=False)
    status = Column(Enum(LOCALSTATUS), nullable=False)
    reschedule = Column(Boolean, nullable=False, default=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    num_completed = Column(Integer, nullable=False, default=0)
    num_failed = Column(Integer, nullable=False, default=0)
    num_submitted = Column(Integer, nullable=False, default=0)

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
                                     g4_version='4.9.5.p02',
                                     physics_version='1.4.0',
                                     se='UKI-LT2-IC-HEP-disk',
                                     unixtime=unixtime,
                                     livetimeperjob=livetimeperjob, **self) as runscript,\
                 temporary_macro(self.tag, self.macro or '', self.app, self.nevents) as macro:
                logger.info("Submitting ParametricJob %s, macro: %s to DIRAC", self.id, self.macro)
                for sublist in list_splitter(range(self.seed, self.seed + self.njobs), 1000):
                    with parametric_job as j:
                        j.setName(os.path.splitext(os.path.basename(macro))[0] + '-%(args)s')
                        j.setPlatform('ANY')
                        j.setExecutable(os.path.basename(runscript),
                                        os.path.basename(macro) + ' %(args)s',
                                        'lzproduction_output.log')
                        j.setInputSandbox([runscript, macro])
                        j.setDestination('ANY')
                        j.setParameterSequence('args', sublist, addToWorkflow=False)
                    dirac_ids.update(parametric_job.subjob_ids)
        else:
            with temporary_runscript(root_version='5.34.32',
                                     root_arch='slc6_gcc44_x86_64',
                                     g4_version='4.9.5.p02',
                                     physics_version='1.4.0',
                                     se='UKI-LT2-IC-HEP-disk', **self) as runscript:
                logger.info("Submitting ParametricJob %s, inputdir: %s to DIRAC", self.id, self.reduction_lfn_inputdir or self.der_lfn_inputdir or self.lzap_lfn_inputdir)

                input_lfn_dir=self.reduction_lfn_inputdir or\
                               self.der_lfn_inputdir or \
                               self.lzap_lfn_inputdir
                for sublist in list_splitter(list_lfns(input_lfn_dir), 1000):
                    with parametric_job as j:
                        j.setName("%(args)s")
                        j.setPlatform('ANY')
                        j.setExecutable(os.path.basename(runscript),
                                        '%(args)s',
                                        'lzanalysis_output.log')
                        j.setInputSandbox([runscript])
                        j.setDestination('ANY')
                        j.setParameterSequence('InputData', sublist, addToWorkflow='ParametricInputData')
                        j.setParameterSequence('args',
                                               [os.path.basename(l) for l in sublist],
                                               addToWorkflow=False)
                    dirac_ids.update(parametric_job.subjob_ids)

        with db_session() as session:
            session.bulk_insert_mappings(DiracJobs, [{'id': i, 'parametricjob_id': self.id}
                                                     for i in parametric_job.subjob_ids])

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
            this.num_completed = local_statuses['Completed']
            this.num_failed = local_statuses['Failed']
            this.num_submitted = local_statuses['Submitted']
            this.reschedule = False
        return status