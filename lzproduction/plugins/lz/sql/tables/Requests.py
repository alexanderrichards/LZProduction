"""Requests Table."""
import logging

import cherrypy
from sqlalchemy import Column, String, Enum

from lzproduction.sql.statuses import LOCALSTATUS
from lzproduction.sql.tables.RequestsBase import RequestsBase

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


@cherrypy.expose
class Requests(RequestsBase):
    """Requests SQL Table."""

    source = Column(String(250), nullable=False)
    detector = Column(String(250), nullable=False)
    sim_lead = Column(String(250), nullable=False)
    status = Column(Enum(LOCALSTATUS), nullable=False, default=LOCALSTATUS.Requested)
    description = Column(String(250), nullable=False)
