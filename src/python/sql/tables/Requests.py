"""Requests Table."""
import logging
from datetime import datetime
import cherrypy
import json
from collections import Mapping
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .SQLTableBase import SQLTableBase
from .ParametricJobs import ParametricJobs
from .Users import Users
from ..utils import db_session
from ..statuses import LOCALSTATUS

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

def subdict(dct, seq, **kwargs):
    """Sub dict."""
    # tuple(seq) as seq might be iterator
    # return {k: v for k, v in dct.iteritems() if k in tulpe(seq)}

    # This might be faster if dct is large as doesn't have to iterate through it.
    # also works natively with seq being an iterator, no tuple initialisation
    return dict({key: dct[key] for key in seq if key in dct}, **kwargs)

class DatetimeMappingEncoder(json.JSONEncoder):
    """JSON encoder for types Datetime and Mapping."""

    def default(self, obj):
        """Override base default method."""
        if isinstance(obj, Mapping):
            return dict(obj, status=obj.status.name)
        if isinstance(obj, datetime):
            return obj.isoformat(' ')
        return super(DatetimeMappingEncoder, self).default(obj)


@cherrypy.expose
class Requests(SQLTableBase):
    """Requests SQL Table."""

    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    requester_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    request_date = Column(String(250), nullable=False)
    source = Column(String(250), nullable=False)
    detector = Column(String(250), nullable=False)
    sim_lead = Column(String(250), nullable=False)
    status = Column(Enum(LOCALSTATUS), nullable=False, default=LOCALSTATUS.Requested)
    description = Column(String(250), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    parametricjobs = relationship("ParametricJobs", back_populates="request")

    def submit(self):
        """Submit Request."""
        with db_session() as session:
            parametricjobs = session.query(ParametricJobs).filter_by(request_id=self.id).all()
            session.expunge_all()
            session.merge(self).status = LOCALSTATUS.Submitting

        logger.info("Submitting request %s", self.id)

        submitted_jobs = []
        try:
            for job in parametricjobs:
                job.submit()
                submitted_jobs.append(job)
        except:
            logger.exception("Exception while submitting request %s", self.id)
            logger.info("Resetting associated ParametricJobs")
            for job in submitted_jobs:
                job.reset()


    def delete_parametric_jobs(self, session):
        """Delete associated ParametricJob jobs."""
        logger.info("Deleting ParametricJobs for Request id: %s", self.id)
        parametric_jobs = session.query(ParametricJobs)\
                                 .filter_by(request_id=self.id)
        for job in parametric_jobs.all():
            job.delete_dirac_jobs(session)
        parametric_jobs.delete(synchronize_session=False)


    def update_status(self):
        """Update request status."""
        with db_session() as session:
            parametricjobs = session.query(ParametricJobs).filter_by(request_id=self.id).all()
            session.expunge_all()

        statuses = []
        for job in parametricjobs:
            try:
                statuses.append(job.update_status())
            except:
                logger.exception("Exception updating ParametricJob %s", job.id)

        status = max(statuses or [self.status])
        if status != self.status:
            with db_session(reraise=False) as session:
                session.merge(self).status = status
            logger.info("Request %s moved to state %s", self.id, status.name)


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
                                      cls=DatetimeMappingEncoder)
                return json.dumps({'data': user_requests.all()}, cls=DatetimeMappingEncoder)

            # Get specific request.
            if requester.admin:
                user_requests = session.query(Requests)
            request = user_requests.filter_by(id=reqid).first()
            return json.dumps({'data': request}, cls=DatetimeMappingEncoder)


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
