"""Certificate authenticated web server."""
import os
import cherrypy
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy_utils import SQLTableBase, create_db, db_session
from apache_utils import check_credentials, AuthenticationError

class Users(SQLTableBase):
    """Users SQL Table."""

    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    dn = Column(String(250), nullable=False)
    ca = Column(String(250), nullable=False)
    suspended = Column(Boolean(), nullable=False)
    admin = Column(Boolean(), nullable=False)


class CertWebServer(object):
    """The Web server."""

    def __init__(self, dburl, html_root):
        """Initialisation."""
        self.dburl = dburl
        create_db(dburl)
        self.html_root = html_root


    @cherrypy.expose
    def index(self):
        """Return the index page."""
        try:
            check_credentials(self.dburl)
        except AuthenticationError as e:
            return e.message

        with open(os.path.join(self.html_root, 'index.html'), 'rb') as front_page:
            return front_page.read()


    @cherrypy.expose
    def newrequest(self):
        """Return the new requests page."""

        try:
            check_credentials(self.dburl)
        except AuthenticationError as e:
            return e.message

        with open(os.path.join(self.html_root, 'newrequest.html')) as new_request:
            return new_request.read().replace('###requester_dn###', clientDN)\
                                     .replace('###requester_ca###', clientCA)
