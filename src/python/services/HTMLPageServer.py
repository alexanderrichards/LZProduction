"""Certificate authenticated web server."""
import os
from datetime import datetime
import cherrypy
import jinja2
from sqlalchemy_utils import create_db, db_session
from tables import Services

MINS = 60
SERVICE_COLOUR_MAP = {'up': 'brightgreen',
                      'down': 'red',
                      'stuck%3F': 'lightgrey'}  # %3F = ?

class HTMLPageServer(object):
    """The Web server."""

    def __init__(self, html_root, dburl):
        """Initialisation."""
        self.html_root = html_root
        self.dburl = dburl
        create_db(dburl)
        self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=html_root))

    @cherrypy.expose
    def index(self):
        """Return the index page."""
        data = {'user': cherrypy.request.verified_user}
        with db_session(self.dburl) as session:
            services = session.query(Services).all()

            for service in services:
                status = service.status
                if (datetime.now() - service.timestamp).total_seconds() > 30. * MINS:
                    status = 'stuck%3F'  # %3F = ?
                data.update({service.name + '_status': status,
                             service.name + '_status_colour': SERVICE_COLOUR_MAP[service.status]})
        return self.template_env.get_template('index.html').render(data)


    @cherrypy.expose
    def newrequest(self):
        """Return the new requests page."""
        with open(os.path.join(self.html_root, 'newrequest.html')) as new_request:
            return new_request.read()
