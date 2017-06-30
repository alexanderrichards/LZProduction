"""Requests Table."""
import os
import logging
import time
import calendar
import re
from itertools import compress
from datetime import datetime
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy import Column, Integer, Boolean, String, PickleType, TIMESTAMP, ForeignKeyConstraint
from sqlalchemy_utils import SQLTableBase, continuing
from dirac_utils import DiracClient
from tempfile_utils import temporary_runscript, temporary_macro

logger = logging.getLogger(__name__)
unixdate = re.compile(r'(?P<month>[0-9]{2})-(?P<day>[0-9]{2})-(?P<year>[0-9]{4})$')


class LongPickleType(PickleType):
    impl = LONGBLOB


class ParametricJobs(SQLTableBase):
    """Jobs SQL Table."""

    __tablename__ = 'parametricjobs'
    id = Column(Integer, primary_key=True)  # pylint: disable=C0103
    request_id = Column(Integer, nullable=False)
    status = Column(String(25), nullable=False)
    macro = Column(String(250), nullable=False)
    tag = Column(String(250), nullable=False)
    app = Column(String(250), nullable=False)
    app_version = Column(String(250))
    fastnest_version = Column(String(250))
    reduction_version = Column(String(250))
    der_version = Column(String(250))
    lzap_version = Column(String(250))
    outputdir_lfns = Column(PickleType())
    njobs = Column(Integer, nullable=False)
    nevents = Column(Integer, nullable=False)
    seed = Column(Integer, nullable=False)
    dirac_jobs = Column(LongPickleType(), nullable=False)
    reschedule = Column(Boolean, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False,
                       default=datetime.utcnow,
                       onupdate=datetime.utcnow)
    ForeignKeyConstraint(['request_id'], ['requests.id'])

    def submit(self, scoped_session):
        lfn_root = os.path.join('/lz/data/MDC1', '_'.join(('-'.join((self.app, self.app_version)),
                                                           '-'.join(('DER', self.der_version)))))
        macro_name = os.path.splitext(os.path.basename(self.macro))[0]
        livetime_sec_per_beamon = 0.1132698957
        livetimeperjob = str(self.nevents * livetime_sec_per_beamon)
        unixtime = time.time()
        match = unixdate.search(macro_name)
        if match is not None:
            month, day, year = match.groups()
            unixtime = str(int(calendar.timegm(datetime(int(year), int(month), int(day), 0, 0).utctimetuple())))
        sim_lfn_dir = os.path.join(lfn_root, macro_name)
        reduction_lfn_dir = os.path.join(lfn_root, 'reduced_v' + (self.reduction_version or ''), macro_name)
        der_lfn_dir = os.path.join(sim_lfn_dir, 'DER')
        lzap_lfn_dir = os.path.join(lfn_root, 'DER-' + (self.der_version or ''),
                                    'LZap-' + (self.lzap_version or ''), macro_name)
        self.outputdir_lfns = list(compress([sim_lfn_dir, reduction_lfn_dir, der_lfn_dir, lzap_lfn_dir],
                                            [self.app_version, self.reduction_version, self.der_version, self.lzap_version]))
        with DiracClient("http://localhost:8000/") as dirac,\
             temporary_runscript(root_version='5.34.32',
                                 root_arch='slc6_gcc44_x86_64',
                                 g4_version='4.9.5.p02',
                                 se='UKI-LT2-IC-HEP-disk',
                                 sim_lfn_dir=sim_lfn_dir,
                                 mctruth_lfn_dir=sim_lfn_dir,
                                 reduction_lfn_dir=reduction_lfn_dir,
                                 der_lfn_dir=der_lfn_dir,
                                 lzap_lfn_dir=lzap_lfn_dir,
                                 seed0=str(self.seed),
                                 unixtime=unixtime,
                                 livetimeperjob=livetimeperjob, **self) as runscript,\
             temporary_macro(self.tag, self.macro, self.app, self.nevents) as macro:
            logger.info("Submitting ParametricJob %s, macro: %s to DIRAC", self.id, self.macro)
            self.status, self.dirac_jobs = dirac.submit_job(runscript,
                                                            macro,
                                                            self.seed,
                                                            self.njobs)

        with continuing(scoped_session) as session:
            this = session.query(ParametricJobs).filter(ParametricJobs.id == self.id).first()
            if this is not None:
                this.status = self.status
                this.outputdir_lfns = self.outputdir_lfns
                this.dirac_jobs = self.dirac_jobs
        return self.status


    def reset(self):
        dirac_ids = self.dirac_jobs
        with DiracClient("http://localhost:8000/") as dirac:
            logger.info("Removing Dirac jobs %s from ParametricJob %s", dirac_ids, self.id)
            dirac.kill(dirac_ids)

    def update_status(self, scoped_session):
        dirac_ids = self.dirac_jobs
        with DiracClient("http://localhost:8000/") as dirac:
            if self.reschedule:
                self.status = dirac.reschedule(dirac_ids)
                self.reschedule = False
            else:
                self.status = dirac.status(dirac_ids)
        if self.status == 'Failed':
            self.status = dirac.auto_reschedule(dirac_ids)

        with continuing(scoped_session) as session:
            this = session.query(ParametricJobs).filter(ParametricJobs.id == self.id).first()
            if this is not None:
                this.status = self.status
        return self.status
