"""Requests Table."""
import os
from itertools import compress
from datetime import datetime
from sqlalchemy import Column, Integer, String, PickleType, TIMESTAMP, ForeignKeyConstraint
from sqlalchemy_utils import SQLTableBase
from dirac_utils import DiracClient
from tempfile_utils import temporary_runscript, temporary_macro


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
    dirac_jobs = Column(PickleType(), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False,
                       default=datetime.utcnow,
                       onupdate=datetime.utcnow)
    ForeignKeyConstraint(['request_id'], ['requests.id'])

    def submit(self):
        lfn_root = os.path.join('/lz/data',
                                '_'.join((self.app, self.app_version, 'geant4.9.5.p02')))
        macro_name = os.path.splitext(os.path.basename(self.macro))[0]
        sim_lfn_dir = os.path.join(lfn_root, macro_name)
        reduction_lfn_dir = os.path.join(lfn_root, 'reduced_v' + (self.reduction_version or ''), macro_name)
        der_lfn_dir = os.path.join(lfn_root, 'DER-' + (self.der_version or ''), macro_name)
        lzap_lfn_dir = os.path.join(lfn_root, 'DER-' + (self.der_version or ''),
                                    'LZap-' + (self.lzap_version or ''), macro_name)
        self.outputdir_lfns = list(compress([sim_lfn_dir, reduction_lfn_dir, der_lfn_dir, lzap_lfn_dir],
                                            [app_version, reduction_version, der_version, lzap_version]))
        with DiracClient("http://localhost:8000/") as dirac,\
             temporary_runscript(root_version='5.34.32',
                                 root_arch='slc6_gcc44_x86_64',
                                 g4_version='4.9.5.p02',
                                 se='UKI-LT2-IC-HEP-disk',
                                 sim_lfn_dir=sim_lfn_dir,
                                 reduction_lfn_dir=reduction_lfn_dir,
                                 der_lfn_dir=der_lfn_der,
                                 lzap_lfn_dir=lzap_lfn_der, **self) as runscript,\
             temporary_macro(self.tag, self.macro, self.app, self.nevents) as macro:
            self.status, self.dirac_jobs = dirac.submit_job(runscript,
                                                            macro,
                                                            self.seed,
                                                            self.njobs)
        return self.status


    def update_status(self):
        with DiracClient("http://localhost:8000/") as dirac:
            self.status, self.dirac_jobs = dirac.status(self.dirac_jobs.keys())
        return self.status
