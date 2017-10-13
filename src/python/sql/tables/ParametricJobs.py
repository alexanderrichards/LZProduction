"""ParametricJobs Table."""
import os
import logging
import time
import calendar
import re
from datetime import datetime
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy import Column, Integer, Boolean, String, PickleType, TIMESTAMP, ForeignKey
from .SQLTableBase import SQLTableBase
from sql.utils import scoped_session
from utils.dirac_utils import DiracClient
from utils.tempfile_utils import temporary_runscript, temporary_macro

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
UNIXDATE = re.compile(r'(?P<month>[0-9]{2})-(?P<day>[0-9]{2})-(?P<year>[0-9]{4})$')


class LongPickleType(PickleType):
    """Pickle type for long blob."""

    impl = LONGBLOB


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
    counters = Column(String(150))
    request_id = Column(Integer, ForeignKey('requests.id'), nullable=False)
    status = Column(String(25), nullable=False)
    dirac_jobs = Column(LongPickleType(), nullable=False)
    reschedule = Column(Boolean, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def submit(self, session_factory):
        """Submit parametric job."""
        # problems here if not running simulation, there will be no macro so
        # everything including context needs reworking.
#        lfn_root = os.path.join('/lz/user/l/lzproduser.grid.hep.ph.ic.ac.uk', '_'.join(('-'.join((self.app, self.app_version)),
#                                                           '-'.join(('DER', self.der_version)))))
        if self.app_version is not None:

            macro_name = os.path.splitext(os.path.basename(self.macro or ''))[0]
            livetime_sec_per_beamon = 0.1132698957
            livetimeperjob = str((self.nevents or 1) * livetime_sec_per_beamon)
            unixtime = time.time()
            match = UNIXDATE.search(macro_name)
            if match is not None:
                month, day, year = match.groups()
                unixtime = str(int(calendar.timegm(datetime(int(year), int(month), int(day), 0, 0).utctimetuple())))
            with DiracClient("http://localhost:8000/") as dirac,\
                 temporary_runscript(root_version='5.34.32',
                                     root_arch='slc6_gcc44_x86_64',
                                     g4_version='4.9.5.p02',
                                     physics_version='1.4.0',
                                     se='UKI-LT2-IC-HEP-disk',
                                     unixtime=unixtime,
                                     livetimeperjob=livetimeperjob, **self) as runscript,\
                 temporary_macro(self.tag, self.macro or '', self.app, self.nevents) as macro:
                logger.info("Submitting ParametricJob %s, macro: %s to DIRAC", self.id, self.macro)
                self.status, self.counters, self.dirac_jobs = dirac.submit_ranged_parametric_job(name=os.path.splitext(os.path.basename(macro))[0] + '-%(args)s',
                                                                                                 executable=os.path.basename(runscript),
                                                                                                 args=os.path.basename(macro) + ' %(args)s',
                                                                                                 input_sandbox=[runscript, macro],
                                                                                                 start=self.seed,
                                                                                                 stop=self.seed + self.njobs,
                                                                                                 output_log='lzproduction_output.log')
        else:
            with DiracClient("http://localhost:8000/") as dirac,\
                 temporary_runscript(root_version='5.34.32',
                                     root_arch='slc6_gcc44_x86_64',
                                     g4_version='4.9.5.p02',
                                     physics_version='1.4.0',
                                     se='UKI-LT2-IC-HEP-disk', **self) as runscript:
                logger.info("Submitting ParametricJob %s, inputdir: %s to DIRAC", self.id, self.reduction_lfn_inputdir or self.der_lfn_inputdir or self.lzap_lfn_inputdir)
                self.status, self.counters, self.dirac_jobs = dirac.submit_lfn_parametric_job(name="%(args)s",
                                                                                              executable=os.path.basename(runscript),
                                                                                              args='%(args)s',
                                                                                              input_sandbox=[runscript],
                                                                                              input_lfn_dir=self.reduction_lfn_inputdir or self.der_lfn_inputdir or self.lzap_lfn_inputdir,
                                                                                              output_log='lzanalysis_output.log')

        with scoped_session(session_factory, reraise=False) as session:
            this = session.query(ParametricJobs).filter(ParametricJobs.id == self.id).first()
            if this is not None:
                this.status = self.status
                this.counters = self.counters
                this.dirac_jobs = self.dirac_jobs
        return self.status

    def reset(self):
        """Reset parametric job."""
        dirac_ids = self.dirac_jobs
        with DiracClient("http://localhost:8000/") as dirac:
            logger.info("Removing Dirac jobs %s from ParametricJob %s", dirac_ids, self.id)
            dirac.kill(dirac_ids)

    def update_status(self, session_factory):
        """Update the status of parametric job."""
        dirac_ids = self.dirac_jobs
        with DiracClient("http://localhost:8000/") as dirac:
            if self.reschedule:
                self.status, self.counters = dirac.reschedule(dirac_ids)
                self.reschedule = False
            else:
                self.status, self.counters = dirac.status(dirac_ids)

            if self.status == 'Failed':
                self.status, self.counters = dirac.auto_reschedule(dirac_ids)

        with scoped_session(session_factory, reraise=False) as session:
            this = session.query(ParametricJobs).filter(ParametricJobs.id == self.id).first()
            if this is not None:
                this.status = self.status
                this.counters = self.counters
                this.reschedule = self.reschedule
        return self.status
