"""Requests Table."""
import json
import logging
from datetime import datetime

import cherrypy
from sqlalchemy import Column, Integer, TEXT, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from lzproduction.utils.collections import subdict
from ..utils import db_session
from ..statuses import LOCALSTATUS
from .SQLTableBase import SQLTableBase
from .JSONTableEncoder import JSONTableEncoder
from .Users import Users
from .ParametricJobs import ParametricJobs


  # pylint: disable=invalid-name


@cherrypy.expose
@cherrypy.popargs('request_id')
class Requests(SQLTableBase):
    """Requests SQL Table."""

    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    requester_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    request_date = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    status = Column(Enum(LOCALSTATUS), nullable=False, default=LOCALSTATUS.Requested)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    parametric_jobs = relationship("ParametricJobs", back_populates="request", cascade="all, delete-orphan")
    parametricjobs = ParametricJobs
    logger = logging.getLogger(__name__)

    def submit(self):
        """Submit Request."""
        with db_session() as session:
            parametricjobs = session.query(ParametricJobs).filter_by(request_id=self.id).all()
            session.expunge_all()
            session.merge(self).status = LOCALSTATUS.Submitting

        self.logger.info("Submitting request %s", self.id)

        submitted_jobs = []
        try:
            for job in parametricjobs:
                job.submit()
                submitted_jobs.append(job)
        except:
            self.logger.exception("Exception while submitting request %s", self.id)
            self.logger.info("Resetting associated ParametricJobs")
            for job in submitted_jobs:
                job.reset()


    def delete_parametric_jobs(self, session):
        """Delete associated ParametricJob jobs."""
        self.logger.info("Deleting ParametricJobs for Request id: %s", self.id)
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
                self.logger.exception("Exception updating ParametricJob %s", job.id)

        status = max(statuses or [self.status])
        if status != self.status:
            with db_session(reraise=False) as session:
                session.merge(self).status = status
            self.logger.info("Request %s moved to state %s", self.id, status.name)


    @classmethod
    @cherrypy.tools.accept(media='application/json')
    @cherrypy.tools.json_out(handler=JSONTableEncoder().default)
    def GET(cls, request_id=None):  # pylint: disable=invalid-name
        """REST Get method."""
#        with cherrypy.HTTPError.handle(ValueError, 400):
#            request_id = int(request_id)
        cls.logger.debug("In GET: reqid = %s", request_id)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            if requester.admin:
                query = session.query(cls, Users).join(Users, cls.requester_id == Users.id)
            else:
                query = session.query(cls).filter_by(requester_id=requester.id)

            if request_id is not None:
                try:
                    request_id = int(request_id)
                except ValueError:
                    raise cherrypy.HTTPError(400, 'Bad request_id')
                query = query.filter_by(id=request_id)

            if requester.admin:
                return [dict(request, requester=user.name, status=request.status.name)
                              for request, user in query.all()]
            return query.all()



    @classmethod
    def DELETE(cls, request_id):  # pylint: disable=invalid-name
        """REST Delete method."""
        cls.logger.debug("In DELETE: reqid = %s", request_id)
        if not cherrypy.request.verified_user.admin:
            raise cherrypy.HTTPError(401, "Unauthorised")
        with db_session() as session:
            cls.logger.info("Deleting Request id: %s", request_id)
            try:
#               request = session.query(Requests).filter_by(id=request_id).delete()
                request = session.query(cls).filter_by(id=request_id).one()
            except NoResultFound:
                message = "No Request found with id: %s" % request_id
                cls.logger.warning(message)
                raise cherrypy.NotFound(message)
            except MultipleResultsFound:
                message = "Multiple Requests found with id: %s!" % request_id
                cls.logger.error(message)
                raise cherrypy.HTTPError(500, message)
            session.delete(request)

    @classmethod
    def PUT(cls, request_id, status):  # pylint: disable=invalid-name
        """REST Put method."""
        cls.logger.debug("In PUT: reqid = %s, status = %s", request_id, status)
        if not cherrypy.request.verified_user.admin:
            raise cherrypy.HTTPError(401, "Unauthorised")

        if status not in LOCALSTATUS:
            raise cherrypy.HTTPError(400, "bad status")

        with db_session() as session:
            try:
                request = session.query(cls).filter_by(id=request_id).one()
            except NoResultFound:
                message = "No Request found with id: %s" % request_id
                cls.logger.warning(message)
                raise cherrypy.NotFound(message)
            except MultipleResultsFound:
                message = "Multiple Requests found with id: %s!" % request_id
                cls.logger.error(message)
                raise cherrypy.HTTPError(500, message)

            request.status = LOCALSTATUS[status]

    @classmethod
    @cherrypy.tools.json_in()
    def POST(cls):  # pylint: disable=invalid-name
        """REST Post method."""
        data = cherrypy.request.json
        cls.logger.debug("In POST: kwargs = %s", data)

        request = Requests(requester_id=cherrypy.request.verified_user.id)
        request.parametric_jobs = []
        for job in data:
            request.parametric_jobs.append(ParametricJobs(**subdict(job,
                                                                   ('allowed'))))
        with db_session() as session:
            session.add(request)
