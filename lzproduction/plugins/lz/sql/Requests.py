"""Requests Table."""
import json
import logging
from datetime import datetime

import cherrypy
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from lzproduction.utils.collections import subdict
from lzproduction.sql.tables import RequestsBase
from ..utils import db_session
from ..statuses import LOCALSTATUS
from .SQLTableBase import SQLTableBase
from .JSONTableEncoder import JSONTableEncoder
from .Users import Users
from .ParametricJobs import ParametricJobs


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


@cherrypy.expose
class Requests(RequestsBase):
    """Requests SQL Table."""
    source = Column(String(250), nullable=False)
    detector = Column(String(250), nullable=False)
    sim_lead = Column(String(250), nullable=False)
    description = Column(String(250), nullable=False)



    @staticmethod
    def GET(reqid=None):  # pylint: disable=invalid-name
        """REST Get method."""
        logger.debug("In GET: reqid = %s", reqid)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            user_requests = session.query(Requests).filter_by(requester_id=requester.id)
            # Get all requests.
            if reqid is None:
                if requester.admin:
                    all_requests = session.query(Requests, Users)\
                                          .join(Users, Requests.requester_id == Users.id)\
                                          .all()
                    # could make a specialised encoder for this.
                    return json.dumps({'data': [dict(request, requester=user.name, status=request.status.name)
                                                for request, user in all_requests]},
                                      cls=JSONTableEncoder)
                return json.dumps({'data': user_requests.all()}, cls=JSONTableEncoder)

            # Get specific request.
            if requester.admin:
                user_requests = session.query(Requests)
            request = user_requests.filter_by(id=reqid).first()
            return json.dumps({'data': request}, cls=JSONTableEncoder)


    @staticmethod
    def DELETE(reqid):  # pylint: disable=invalid-name
        """REST Delete method."""
        logger.debug("In DELETE: reqid = %s", reqid)
        if cherrypy.request.verified_user.admin:
            with db_session() as session:
                logger.info("Deleting Request id: %s", reqid)
                try:
                    request = session.query(Requests).filter_by(id=reqid).one()
                except NoResultFound:
                    logger.warning("No Request found with id: %s", reqid)
                except MultipleResultsFound:
                    logger.error("Multiple Requests found with id: %s!", reqid)
                else:
                    request.delete_parametric_jobs(session)
                    session.delete(request)
        return Requests.GET()

    @staticmethod
    def PUT(reqid, **kwargs):  # pylint: disable=invalid-name
        """REST Put method."""
        logger.debug("In PUT: reqid = %s, kwargs = %s", reqid, kwargs)
        requester = cherrypy.request.verified_user

        status_update = kwargs.pop('status', None)
        with db_session() as session:
            query = session.query(Requests).filter_by(id=reqid)
            if requester.admin and status_update == 'Approved':
                query.update(subdict(kwargs, ('description',
                                              'sim_lead',
                                              'detector',
                                              'source'), status=LOCALSTATUS.Approved))
                return Requests.GET()

            if not requester.admin:
                query = query.filter_by(requester_id=requester.id)
            query.update(subdict(kwargs, ('description', 'sim_lead', 'detector', 'source')))

        return Requests.GET()

    @staticmethod
    def POST(**kwargs):  # pylint: disable=invalid-name
        """REST Post method."""
        logger.debug("In POST: kwargs = %s", kwargs)
        selected_macros = kwargs.pop('selected_macros', [])
        if not isinstance(selected_macros, list):
            selected_macros = [selected_macros]

        with db_session() as session:
            request = Requests(**subdict(kwargs, Requests.columns,
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
                logger.warning("No ParametricJobs added to the DB.")
        return Requests.GET()
