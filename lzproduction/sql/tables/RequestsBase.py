"""Requests Table."""
import json
import logging
from abc import abstractmethod
from datetime import datetime

import cherrypy
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from ..utils import db_session
from ..statuses import LOCALSTATUS
from .SQLTableBase import SQLTableBase
from .JSONTableEncoder import JSONTableEncoder
from .Users import Users


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
    logger = logging.getLogger(__name__)

    def add(self):
        """Add instance to the db."""
        with db_session() as session:
            session.add(self)

    def delete(self):
        """Delete instance from session."""
        with db_session() as session:
            session.delete(self)

    def submit(self):
        """Submit Request."""
        self.logger.info("Submitting request %s", self.id)
        self.status = LOCALSTATUS.Submitting

        submitted_jobs = []
        try:
            for job in self.parametricjobs:
                job.submit()
                submitted_jobs.append(job)
        except:
            self.logger.exception("Exception while submitting request %s", self.id)
            self.logger.info("Resetting associated ParametricJobs")
            for job in submitted_jobs:
                job.reset()

    def update_status(self):
        """Update request status."""
        statuses = []
        for job in self.parametricjobs:
            try:
                statuses.append(job.update_status())
            except:
                self.logger.exception("Exception updating ParametricJob %s", job.id)

        status = max(statuses or [self.status])
        if status != self.status:
            self.status = status
            self.logger.info("Request %s moved to state %s", self.id, status.name)

    @classmethod
    def GET(cls, reqid=None):  # pylint: disable=invalid-name
        """REST Get method."""
        cls.logger.debug("In GET: reqid = %s", reqid)
        requester = cherrypy.request.verified_user
        with db_session() as session:
            user_requests = session.query(cls).filter_by(requester_id=requester.id)
            # Get all requests.
            if reqid is None:
                if requester.admin:
                    all_requests = session.query(cls, Users)\
                                          .join(Users, cls.requester_id == Users.id)\
                                          .all()
                    # could make a specialised encoder for this.
                    return json.dumps({'data': [dict(request, requester=user.name, status=request.status.name)
                                                for request, user in all_requests]},
                                      cls=JSONTableEncoder)
                return json.dumps({'data': user_requests.all()}, cls=JSONTableEncoder)

            # Get specific request.
            if requester.admin:
                user_requests = session.query(cls)
            request = user_requests.filter_by(id=reqid).first()
            return json.dumps({'data': request}, cls=JSONTableEncoder)

    @classmethod
    def DELETE(cls, reqid):  # pylint: disable=invalid-name
        """REST Delete method."""
        cls.logger.debug("In DELETE: reqid = %s", reqid)
        if cherrypy.request.verified_user.admin:
            with db_session() as session:
                cls.logger.info("Deleting Request id: %s", reqid)
                try:
                    request = session.query(cls).filter_by(id=reqid).one()
                except NoResultFound:
                    cls.logger.warning("No Request found with id: %s", reqid)
                except MultipleResultsFound:
                    cls.logger.error("Multiple Requests found with id: %s!", reqid)
                else:
                    session.delete(request)
        return cls.GET()

    @classmethod
    @abstractmethod
    def PUT(cls, reqid, **kwargs):  # pylint: disable=invalid-name
        """REST Put method."""
        return cls.GET()

    @classmethod
    @abstractmethod
    def POST(cls, **kwargs):  # pylint: disable=invalid-name
        """REST Post method."""
        cls(**kwargs).add()
        return cls.GET()
