"""ParametricJobs Table."""
import os
import re
import time
import json
import logging
import calendar
from datetime import datetime

import cherrypy
from sqlalchemy import Column, Integer, Boolean, String, PickleType, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from lzproduction.rpc.DiracRPCClient import dirac_api_client, ParametricDiracJobClient
from lzproduction.utils.collections import list_splitter
from lzproduction.utils.tempfile_utils import temporary_runscript, temporary_macro
from lzproduction.sql.utils import db_session
from lzproduction.sql.statuses import LOCALSTATUS
from lzproduction.sql.tables.ParametricJobsBase import ParametricJobsBase
from lzproduction.sql.tables.JSONTableEncoder import JSONTableEncoder
from lzproduction.sql.tables.DiracJobs import DiracJobs


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
UNIXDATE = re.compile(r'(?P<month>[0-9]{2})-(?P<day>[0-9]{2})-(?P<year>[0-9]{4})$')


@cherrypy.expose
class ParametricJobs(ParametricJobsBase):
    """Jobs SQL Table."""

    app = Column(String(250))
    app_version = Column(String(250))
    sim_lfn_outputdir = Column(String(250))
    mctruth_lfn_outputdir = Column(String(250))
    macro = Column(String(250))
    tag = Column(String(250))
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



    def job_config(self):
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
            with temporary_runscript(root_version='5.34.32',
                                     root_arch='slc6_gcc44_x86_64',
                                     g4_version='4.10.03.p02',
                                     physics_version='1.4.0',
                                     se='UKI-LT2-IC-HEP-disk',
                                     unixtime=unixtime,
                                     livetimeperjob=livetimeperjob, **self) as runscript,\
                 temporary_macro(self.tag, self.macro or '', self.app, self.app_version, self.nevents) as macro:
                logger.info("Submitting ParametricJob %s, macro: %s to DIRAC", self.id, self.macro)
                for sublist in list_splitter(range(self.seed, self.seed + self.num_jobs), 1000):
                    job = (yield)
                    job.setName(os.path.splitext(os.path.basename(macro))[0] + '-%(args)s')
                    job.setPlatform('ANY')
                    job.setExecutable(os.path.basename(runscript),
                                    os.path.basename(macro) + ' %(args)s',
                                    'lzproduction_output.log')
                    job.setInputSandbox([runscript, macro])
                    job.setParameterSequence('args', sublist, addToWorkflow=False)
        else:
            with temporary_runscript(root_version='5.34.32',
                                     root_arch='slc6_gcc44_x86_64',
                                     g4_version='4.10.03.p02',
                                     physics_version='1.4.0',
                                     se='UKI-LT2-IC-HEP-disk', **self) as runscript:
                logger.info("Submitting ParametricJob %s, inputdir: %s to DIRAC", self.id, self.reduction_lfn_inputdir or self.der_lfn_inputdir or self.lzap_lfn_inputdir)

                input_lfn_dir=self.reduction_lfn_inputdir or\
                               self.der_lfn_inputdir or \
                               self.lzap_lfn_inputdir
                for sublist in list_splitter(list_lfns(input_lfn_dir), 1000):
                    job = (yield)
                    job.setName("%(args)s")
                    job.setPlatform('ANY')
                    job.setExecutable(os.path.basename(runscript),
                                    '%(args)s',
                                    'lzanalysis_output.log')
                    job.setInputSandbox([runscript])
                    job.setParameterSequence('InputData', sublist, addToWorkflow='ParametricInputData')
                    job.setParameterSequence('args',
                                           [os.path.basename(l) for l in sublist],
                                           addToWorkflow=False)
