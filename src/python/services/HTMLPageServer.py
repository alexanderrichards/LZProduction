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
                      'unknown': 'lightgrey',
                      'stuck%3F': 'yellow'}  # %3F = ?


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
            gangad = session.query(Services).filter(Services.name == 'gangad').one_or_none()
            if gangad is None:
                data.update({'gangad_status': 'Not in DB!', 'gangad_status_colour': 'red'})
                return self.template_env.get_template('index.html').render(data)

            nongangad_services = session.query(Services).filter(Services.name != 'gangad').all()
            out_of_date = (datetime.now() - gangad.timestamp).total_seconds() > 30. * MINS
            if gangad.status == 'down' or out_of_date:
                nongangad_services = (Services(name=service.name, status='unknown') for service in nongangad_services)
                if gangad.status != 'down':
                    gangad = Services(name=gangad.name, status='stuck%3F')  # %3F = ?

            data.update({'gangad_status': gangad.status,
                         'gangad_status_colour': SERVICE_COLOUR_MAP[gangad.status]})
            for service in nongangad_services:
                data.update({service.name + '_status': service.status,
                             service.name + '_status_colour': SERVICE_COLOUR_MAP[service.status]})
        return self.template_env.get_template('index.html').render(data)

    @cherrypy.expose
    def newrequest(self):
        """Return the new requests page."""
        with open(os.path.join(self.html_root, 'newrequest.html')) as new_request:
            return new_request.read()
