"""Requests Table."""
import json
import logging
from datetime import datetime

import cherrypy
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from lzproduction.utils.collections import subdict
from ..utils import db_session
from ..statuses import LOCALSTATUS
from .SQLTableBase import SQLTableBase
from .JSONTableEncoder import JSONTableEncoder
from .Users import Users
from .ParametricJobsBase import ParametricJobsBase


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


@cherrypy.expose
class RequestsBase(SQLTableBase):
    """Requests SQL Table."""

    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    requester_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    request_date = Column(String(10), nullable=False, default=lambda: datetime.today().strftime('%d/%m/%Y'))
    status = Column(Enum(LOCALSTATUS), nullable=False, default=LOCALSTATUS.Requested)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    parametricjobs = relationship("ParametricJobs", back_populates="request", cascade="all, delete-orphan")

    def submit(self):
        """Submit Request."""
        logger.info("Submitting request %s", self.id)
        self.status = LOCALSTATUS.Submitting

        submitted_jobs = []
        try:
            for job in self.parametricjobs:
                job.submit()
                submitted_jobs.append(job)
        except:
            logger.exception("Exception while submitting request %s", self.id)
            logger.info("Resetting associated ParametricJobs")
            for job in submitted_jobs:
                job.reset()


    def update_status(self):
        """Update request status."""
        statuses = []
        for job in self.parametricjobs:
            try:
                statuses.append(job.update_status())
            except:
                logger.exception("Exception updating ParametricJob %s", job.id)

        status = max(statuses or [self.status])
        if status != self.status:
            self.status = status
            logger.info("Request %s moved to state %s", self.id, status.name)


    @staticmethod
    def GET(reqid=None):  # pylint: disable=invalid-name
        """REST Get method."""
        logger.debug("In GET: reqid = %s", reqid)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            user_requests = session.query(RequestsBase).filter_by(requester_id=requester.id)
            # Get all requests.
            if reqid is None:
                if requester.admin:
                    all_requests = session.query(RequestsBase, Users)\
                                          .join(Users, RequestsBase.requester_id == Users.id)\
                                          .all()
                    # could make a specialised encoder for this.
                    return json.dumps({'data': [dict(request, requester=user.name, status=request.status.name)
                                                for request, user in all_requests]},
                                      cls=JSONTableEncoder)
                return json.dumps({'data': user_requests.all()}, cls=JSONTableEncoder)

            # Get specific request.
            if requester.admin:
                user_requests = session.query(RequestsBase)
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
                    request = session.query(RequestsBase).filter_by(id=reqid).one()
                except NoResultFound:
                    logger.warning("No Request found with id: %s", reqid)
                except MultipleResultsFound:
                    logger.error("Multiple Requests found with id: %s!", reqid)
                else:
                    request.delete_parametric_jobs(session)
                    session.delete(request)
        return RequestsBase.GET()

    @staticmethod
    def PUT(reqid, **kwargs):  # pylint: disable=invalid-name
        """REST Put method."""
        logger.debug("In PUT: reqid = %s, kwargs = %s", reqid, kwargs)
        requester = cherrypy.request.verified_user

        status_update = kwargs.pop('status', None)
        with db_session() as session:
            query = session.query(RequestsBase).filter_by(id=reqid)
            if requester.admin and status_update == 'Approved':
                query.update(subdict(kwargs, ('description',
                                              'sim_lead',
                                              'detector',
                                              'source'), status=LOCALSTATUS.Approved))
                return RequestsBase.GET()

            if not requester.admin:
                query = query.filter_by(requester_id=requester.id)
            query.update(subdict(kwargs, ('description', 'sim_lead', 'detector', 'source')))

        return RequestsBase.GET()

    @staticmethod
    def POST(**kwargs):  # pylint: disable=invalid-name
        """REST Post method."""
        logger.debug("In POST: kwargs = %s", kwargs)
        selected_macros = kwargs.pop('selected_macros', [])
        if not isinstance(selected_macros, list):
            selected_macros = [selected_macros]

        with db_session() as session:
            request = RequestsBase(**subdict(kwargs, RequestsBase.columns,
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
                    parametricjobs.append(subdict(kwargs, ParametricJobsBase.columns,
                                                  request_id=request.id,
                                                  status=LOCALSTATUS.Requested,
                                                  macro=path,
                                                  njobs=njobs,
                                                  nevents=nevents,
                                                  seed=seed))
            elif kwargs.viewkeys() & {'reduction_lfn_inputdir',
                                      'der_lfn_inputdir',
                                      'lzap_lfn_inputdir'}:
                parametricjobs.append(subdict(kwargs, ParametricJobsBase.columns,
                                              request_id=request.id,
                                              status=LOCALSTATUS.Requested))


            if parametricjobs:
                session.bulk_insert_mappings(ParametricJobsBase, parametricjobs)
            else:
                logger.warning("No ParametricJobs added to the DB.")
        return RequestsBase.GET()
