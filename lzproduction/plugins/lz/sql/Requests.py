"""Requests Table."""
import logging
from datetime import datetime

import cherrypy
from sqlalchemy import Column, String

from lzproduction.utils.collections import subdict
from lzproduction.sql.tables import RequestsBase
from lzproduction.sql.utils import db_session
from lzproduction.sql.statuses import LOCALSTATUS
from .ParametricJobs import ParametricJobs




@cherrypy.expose
class Requests(RequestsBase):
    """Requests SQL Table."""
    source = Column(String(250), nullable=False)
    detector = Column(String(250), nullable=False)
    sim_lead = Column(String(250), nullable=False)
    description = Column(String(250), nullable=False)
    logger = logging.getLogger(__name__)

    @classmethod
    def PUT(cls, reqid, **kwargs):  # pylint: disable=invalid-name
        """REST Put method."""
        cls.logger.debug("In PUT: reqid = %s, kwargs = %s", reqid, kwargs)
        requester = cherrypy.request.verified_user

        status_update = kwargs.pop('status', None)
        with db_session() as session:
            query = session.query(cls).filter_by(id=reqid)
            if requester.admin and status_update == 'Approved':
                query.update(subdict(kwargs, ('description',
                                              'sim_lead',
                                              'detector',
                                              'source'), status=LOCALSTATUS.Approved))
                return cls.GET()

            if not requester.admin:
                query = query.filter_by(requester_id=requester.id)
            query.update(subdict(kwargs, ('description', 'sim_lead', 'detector', 'source')))

        return cls.GET()

    @classmethod
    def POST(cls, **kwargs):  # pylint: disable=invalid-name
        """REST Post method."""
        cls.logger.debug("In POST: kwargs = %s", kwargs)
        selected_macros = kwargs.pop('selected_macros', [])
        if not isinstance(selected_macros, list):
            selected_macros = [selected_macros]

        with db_session() as session:
            request = cls(**subdict(kwargs, cls.columns,
                                         requester_id=cherrypy.request.verified_user.id,
                                         request_date=datetime.now().strftime('%d/%m/%Y'),
                                         status=LOCALSTATUS.Requested))
            session.add(request)
            session.flush()
            session.refresh(request)

            parametricjobs = []
            if 'app' in kwargs:
                for macro in selected_macros:
                    path, njobs, nevents, seed = macro.split()
                    parametricjobs.append(subdict(kwargs, ParametricJobs.columns,
                                                  request_id=request.id,
                                                  status=LOCALSTATUS.Requested,
                                                  macro=path,
                                                  njobs=njobs,
                                                  nevents=nevents,
                                                  seed=seed))
            elif kwargs.viewkeys() & {'reduction_lfn_inputdir',
                                      'der_lfn_inputdir',
                                      'lzap_lfn_inputdir'}:
                parametricjobs.append(subdict(kwargs, ParametricJobs.columns,
                                              request_id=request.id,
                                              status=LOCALSTATUS.Requested))


            if parametricjobs:
                session.bulk_insert_mappings(ParametricJobs, parametricjobs)
            else:
                cls.logger.warning("No ParametricJobs added to the DB.")
        return cls.GET()
