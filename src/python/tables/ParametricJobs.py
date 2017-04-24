"""Requests Table."""
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
    request = Column(String(250))
    reduction_version = Column(String(250), nullable=False)
    reduced_lfns = Column(PickleType())
    njobs = Column(Integer, nullable=False)
    nevents = Column(Integer, nullable=False)
    seed = Column(Integer, nullable=False)
    dirac_jobs = Column(PickleType(), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False,
                       default=datetime.utcnow,
                       onupdate=datetime.utcnow)
    ForeignKeyConstraint(['request_id'], ['requests.id'])

    def submit(self):
        with DiracClient("http://localhost:8000/") as dirac,\
             temporary_runscript(root_version='5.34.32',
                                 root_arch='slc6_gcc44_x86_64',
                                 g4_version='4.9.5.p02', **self) as runscript,\
             temporary_macro(self.tag, self.macro, self.app, self.nevents) as macro:
            self.status, self.dirac_jobs = dirac.submit_job(self.request_id,
                                                            runscript.name,
                                                            macro.name,
                                                            self.seed,
                                                            self.njobs)
        return self.status


    def update_status(self):
        with DiracClient("http://localhost:8000/") as dirac:
            self.status, self.dirac_jobs = dirac.status(self.dirac_jobs.keys())
        return self.status
